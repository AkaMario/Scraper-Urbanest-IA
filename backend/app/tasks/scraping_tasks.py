from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from sqlalchemy import and_, func, or_, select, text

from app.database import SessionLocal
from app.models import Property, ScrapingJob, SearchQuery
from app.services.cartagena_locations import location_search_terms, nearby_neighborhoods
from app.services.property_analyzer import analyze_properties
from app.services.embeddings import generate_embedding, to_pgvector_literal
from app.services.property_store import ensure_property_storage, mark_missing_properties_inactive, upsert_property
from app.services.query_parser import parse_user_query
from scraper.normalizer import normalize_property, property_matches_query, run_live_property_search, run_property_search

from .celery_app import celery


ACTIVE_PROPERTY_SOURCES = ("FincaRaiz", "Metrocuadrado")
logger = logging.getLogger(__name__)


def _zone_like(value: str) -> str:
    return f"%{value.strip().lower()}%"


def _selected_sources(parsed_query: dict) -> tuple[str, ...]:
    requested = tuple(
        source
        for source in parsed_query.get("sources") or ACTIVE_PROPERTY_SOURCES
        if source in ACTIVE_PROPERTY_SOURCES
    )
    return requested or ACTIVE_PROPERTY_SOURCES


def _ensure_property_detail_columns(db) -> None:
    ensure_property_storage(db)


def _normalize_results_for_query(raw_results: list[dict], parsed_query: dict) -> list[dict]:
    return [
        normalized
        for normalized in (normalize_property(item, parsed_query) for item in raw_results)
        if property_matches_query(normalized, parsed_query)
    ]


def _run_search_scope(parsed_query: dict) -> list[dict]:
    return _normalize_results_for_query(run_property_search(parsed_query), parsed_query)


def _property_filters(stmt, parsed_query: dict, strict: bool = True):
    city = parsed_query.get("city") or "Cartagena"
    stmt = stmt.where(func.lower(Property.city) == city.lower(), Property.status == "active")
    if parsed_query.get("operation"):
        stmt = stmt.where(Property.operation == parsed_query["operation"])
    if parsed_query.get("property_type") and strict:
        stmt = stmt.where(func.lower(Property.property_type) == parsed_query["property_type"].lower())
    if parsed_query.get("price_min") and strict:
        stmt = stmt.where(Property.price >= int(parsed_query["price_min"]))
    if parsed_query.get("price_max") and strict:
        stmt = stmt.where(Property.price <= int(parsed_query["price_max"]))
    if parsed_query.get("bedrooms") and strict:
        stmt = stmt.where(Property.bedrooms >= int(parsed_query["bedrooms"]))
    if parsed_query.get("bathrooms") and strict:
        stmt = stmt.where(Property.bathrooms >= int(parsed_query["bathrooms"]))
    return stmt


def search_saved_properties(db, parsed_query: dict, user_message: str, limit: int = 24) -> list[Property]:
    embedding = to_pgvector_literal(generate_embedding(user_message))
    if db.bind.dialect.name == "postgresql" and embedding:
        base_sql = """
            SELECT * FROM properties
            WHERE lower(city) = lower(:city)
              AND status = 'active'
              AND (:operation IS NULL OR operation = :operation)
              AND (:property_type IS NULL OR lower(property_type) = lower(:property_type))
              AND (:price_min IS NULL OR price >= :price_min)
              AND (:price_max IS NULL OR price <= :price_max)
              AND (:bedrooms IS NULL OR bedrooms >= :bedrooms OR bedrooms IS NULL)
              AND (:bathrooms IS NULL OR bathrooms >= :bathrooms OR bathrooms IS NULL)
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """
        rows = db.execute(
            select(Property).from_statement(text(base_sql)),
            {
                "city": parsed_query.get("city") or "Cartagena",
                "operation": parsed_query.get("operation"),
                "property_type": parsed_query.get("property_type"),
                "price_min": parsed_query.get("price_min"),
                "price_max": parsed_query.get("price_max"),
                "bedrooms": parsed_query.get("bedrooms"),
                "bathrooms": parsed_query.get("bathrooms"),
                "embedding": embedding,
                "limit": limit,
            },
        ).scalars().all()
        if rows:
            return list(rows)

    stmt = _property_filters(select(Property), parsed_query).order_by(Property.last_seen_at.desc()).limit(limit)
    rows = list(db.execute(stmt).scalars().all())
    if rows:
        return rows

    fallback_stmt = _property_filters(select(Property), parsed_query, strict=False).order_by(Property.last_seen_at.desc()).limit(limit)
    return list(db.execute(fallback_stmt).scalars().all())


def _search_with_nearby_fallback(parsed_query: dict) -> list[dict]:
    requested_zone = parsed_query.get("zone") or parsed_query.get("neighborhood")
    if not requested_zone:
        exact_results = _normalize_results_for_query(run_property_search(parsed_query), parsed_query)
        parsed_query["accepted_zones"] = location_search_terms(parsed_query.get("zone") or parsed_query.get("neighborhood"))
        parsed_query["location_match_scope"] = "exact"
        return exact_results

    search_scopes = [("exact", requested_zone, parsed_query)]
    for nearby_zone in nearby_neighborhoods(requested_zone):
        nearby_query = {**parsed_query, "zone": nearby_zone, "neighborhood": nearby_zone, "accepted_zones": [nearby_zone]}
        search_scopes.append(("nearby", nearby_zone, nearby_query))

    scoped_results: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(search_scopes)) as executor:
        future_map = {
            executor.submit(_run_search_scope, query): (scope, zone)
            for scope, zone, query in search_scopes
        }
        for future in as_completed(future_map):
            scope, zone = future_map[future]
            scoped_results[f"{scope}:{zone}"] = future.result()

    exact_results = scoped_results.get(f"exact:{requested_zone}") or []
    if exact_results:
        parsed_query["accepted_zones"] = location_search_terms(requested_zone)
        parsed_query["location_match_scope"] = "exact"
        parsed_query["nearby_zones_checked"] = []
        return exact_results

    nearby_zones = nearby_neighborhoods(requested_zone)
    for nearby_zone in nearby_neighborhoods(requested_zone):
        zone_results = scoped_results.get(f"nearby:{nearby_zone}") or []
        if zone_results:
            parsed_query["accepted_zones"] = [nearby_zone]
            parsed_query["location_match_scope"] = "nearby"
            parsed_query["nearby_zones_checked"] = nearby_zones
            return zone_results

    parsed_query["accepted_zones"] = location_search_terms(requested_zone)
    parsed_query["location_match_scope"] = "exact"
    parsed_query["nearby_zones_checked"] = nearby_zones
    return []


@celery.task(name="app.tasks.scraping_tasks.process_search_request")
def process_search_request(job_id: int, query_id: int, user_message: str) -> dict:
    db = SessionLocal()
    try:
        job = db.get(ScrapingJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} no encontrado")

        job.status = "parsing"
        job.started_at = datetime.utcnow()
        job.error_message = None
        db.commit()

        parsed_query, parser_used = parse_user_query(user_message)
        job.status = "searching_database"
        db.commit()

        _ensure_property_detail_columns(db)
        saved_results = search_saved_properties(db, parsed_query, user_message)

        search_query = db.get(SearchQuery, query_id)
        if search_query:
            search_query.parsed_query_json = parsed_query
            db.commit()

        job.status = "completed"
        job.finished_at = datetime.utcnow()
        db.commit()

        serialized_results = [
            {
                "title": item.title,
                "description": item.description,
                "city": item.city,
                "zone": item.zone,
                "neighborhood": item.neighborhood,
                "property_type": item.property_type,
                "operation": item.operation,
                "price": item.price,
                "bedrooms": item.bedrooms,
                "bathrooms": item.bathrooms,
                "parking_spaces": item.parking_spaces,
                "stratum": item.stratum,
                "area_m2": float(item.area_m2) if item.area_m2 is not None else None,
                "features": item.features or [],
                "source": item.source,
                "url": item.url,
                "image_url": item.image_url,
                "image_urls": item.image_urls or [],
            }
            for item in saved_results
        ]
        analysis = analyze_properties(serialized_results)
        return {
            "job_id": job_id,
            "parser_used": parser_used,
            "parsed_query": parsed_query,
            "result_count": len(serialized_results),
            "analysis": analysis,
        }
    except Exception as exc:
        db.rollback()
        job = db.get(ScrapingJob, job_id)
        if job:
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            job.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()


def get_job_results(db, job_id: int) -> list[Property]:
    job = db.get(ScrapingJob, job_id)
    if not job:
        return []
    query = db.get(SearchQuery, job.query_id)
    parsed_query = (query.parsed_query_json if query else {}) or {}
    if query:
        return search_saved_properties(db, parsed_query, query.user_message)
    stmt = select(Property).where(func.lower(Property.city) == parsed_query.get("city", "Cartagena").lower())
    accepted_zones = parsed_query.get("accepted_zones") or location_search_terms(parsed_query.get("zone") or parsed_query.get("neighborhood"))
    if accepted_zones:
        requested_zones = [_zone_like(zone) for zone in accepted_zones]
        unknown_zone = or_(Property.zone.is_(None), func.lower(Property.zone).in_(["", "cartagena"]))
        unknown_neighborhood = or_(
            Property.neighborhood.is_(None),
            func.lower(Property.neighborhood).in_(["", "cartagena"]),
        )
        stmt = stmt.where(
            or_(
                *(func.lower(Property.zone).like(zone) for zone in requested_zones),
                *(func.lower(Property.neighborhood).like(zone) for zone in requested_zones),
                and_(
                    unknown_zone,
                    unknown_neighborhood,
                    or_(
                        *(func.lower(Property.title).like(zone) for zone in requested_zones),
                        *(func.lower(Property.description).like(zone) for zone in requested_zones),
                        *(func.lower(Property.url).like(zone) for zone in requested_zones),
                    ),
                ),
            )
        )
    if parsed_query.get("property_type"):
        stmt = stmt.where(func.lower(Property.property_type) == parsed_query["property_type"].lower())
    stmt = stmt.where(Property.source.in_(_selected_sources(parsed_query)))
    if job.started_at:
        stmt = stmt.where(Property.scraped_at >= job.started_at)
    if job.finished_at:
        stmt = stmt.where(Property.scraped_at <= job.finished_at)
    return list(db.execute(stmt.order_by(Property.scraped_at.desc())).scalars().all())


@celery.task(name="app.tasks.scraping_tasks.refresh_property_inventory", soft_time_limit=3300, time_limit=3600)
def refresh_property_inventory() -> dict:
    cities = ("Cartagena", "Barranquilla")
    operations = ("rent", "sale")
    sources = ("FincaRaiz", "Metrocuadrado")
    db = SessionLocal()
    summary = {"scraped": 0, "upserted": 0, "scopes": []}
    try:
        ensure_property_storage(db)
        for city in cities:
            for operation in operations:
                query = {"city": city, "operation": operation, "sources": list(sources)}
                started_at = datetime.utcnow()
                raw_results = run_live_property_search(query)
                normalized_results = _normalize_results_for_query(raw_results, query)
                summary["scraped"] += len(raw_results)
                seen_by_source = {source: set() for source in sources}
                for item in normalized_results:
                    try:
                        upsert_property(db, item)
                        db.commit()
                        seen_by_source.setdefault(item["source"], set()).add(item["url"])
                        summary["upserted"] += 1
                    except Exception as exc:
                        db.rollback()
                        logger.exception("Could not persist property %s: %s", item.get("url"), exc)
                for source, seen_urls in seen_by_source.items():
                    mark_missing_properties_inactive(db, city, source, operation, seen_urls, started_at)
                summary["scopes"].append({"city": city, "operation": operation, "count": len(normalized_results)})
                db.commit()
        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
