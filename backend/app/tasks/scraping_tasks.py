from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import os

from sqlalchemy import and_, func, or_, select, text

from app.database import SessionLocal
from app.models import Property, ScrapingJob, SearchQuery
from app.services.cartagena_locations import NEIGHBORHOOD_ALIASES, location_search_terms, nearby_neighborhoods
from app.services.property_analyzer import analyze_properties
from app.services.embeddings import generate_embedding, to_pgvector_literal
from app.services.property_store import ensure_property_storage, mark_missing_properties_inactive, upsert_property
from app.services.query_parser import parse_user_query
from scraper.normalizer import normalize_property, property_matches_query, run_live_property_search, run_property_search

from .celery_app import celery


ACTIVE_PROPERTY_SOURCES = ("FincaRaiz", "Metrocuadrado")
logger = logging.getLogger(__name__)
MISSING_INACTIVE_THRESHOLD = int(os.getenv("MISSING_INACTIVE_THRESHOLD", "3"))

BARRANQUILLA_NEIGHBORHOODS = (
    "Alto Prado",
    "Villa Santos",
    "Riomar",
    "Buenavista",
    "El Golf",
    "Ciudad Jardin",
    "La Campina",
    "Miramar",
    "Villa Carolina",
    "Paraiso",
    "Boston",
    "El Prado",
    "Las Delicias",
    "La Concepcion",
    "El Recreo",
    "Colombia",
    "Los Andes",
    "San Vicente",
    "Altos de Riomar",
    "La Castellana",
)


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
    location_term = _primary_location_term(parsed_query)
    if location_term:
        location_like = _zone_like(location_term)
        stmt = stmt.where(
            or_(
                func.lower(Property.zone).like(location_like),
                func.lower(Property.neighborhood).like(location_like),
                func.lower(Property.title).like(location_like),
                func.lower(Property.description).like(location_like),
            )
        )
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
    if parsed_query.get("parking_spaces") and strict:
        stmt = stmt.where(or_(Property.parking_spaces >= int(parsed_query["parking_spaces"]), Property.parking_spaces.is_(None)))
    return stmt


def _primary_location_term(parsed_query: dict) -> str | None:
    accepted_zones = parsed_query.get("accepted_zones") or location_search_terms(
        parsed_query.get("zone") or parsed_query.get("neighborhood")
    )
    return str(accepted_zones[0]).strip().lower() if accepted_zones else None


def _location_terms(parsed_query: dict) -> list[str]:
    accepted_zones = parsed_query.get("accepted_zones") or location_search_terms(
        parsed_query.get("zone") or parsed_query.get("neighborhood")
    )
    return [str(zone).strip().lower() for zone in accepted_zones if str(zone).strip()]


def _price_window_query(parsed_query: dict, margin: float = 0.10) -> dict:
    query = dict(parsed_query)
    reference_price = query.get("price_max") or query.get("price_min")
    if reference_price:
        reference_price = int(reference_price)
        query["price_min"] = int(reference_price * (1 - margin))
        query["price_max"] = int(reference_price * (1 + margin))
    return query


def _semantic_property_search(
    db,
    parsed_query: dict,
    embedding: str,
    *,
    strict: bool,
    require_location: bool,
    limit: int,
) -> list[Property]:
    location_terms = _location_terms(parsed_query) if require_location else []
    location_likes = [f"%{term}%" for term in location_terms]
    base_sql = """
        SELECT * FROM properties
        WHERE lower(city) = lower(:city)
          AND status = 'active'
          AND (:operation IS NULL OR operation = :operation)
          AND (:require_location IS FALSE OR lower(coalesce(zone, '')) LIKE ANY(:location_likes)
            OR lower(coalesce(neighborhood, '')) LIKE ANY(:location_likes)
            OR lower(coalesce(title, '')) LIKE ANY(:location_likes)
            OR lower(coalesce(description, '')) LIKE ANY(:location_likes))
          AND (:strict_filters IS FALSE OR :property_type IS NULL OR lower(property_type) = lower(:property_type))
          AND (:strict_filters IS FALSE OR :price_min IS NULL OR price >= :price_min)
          AND (:strict_filters IS FALSE OR :price_max IS NULL OR price <= :price_max)
          AND (:strict_filters IS FALSE OR :bedrooms IS NULL OR bedrooms >= :bedrooms OR bedrooms IS NULL)
          AND (:strict_filters IS FALSE OR :bathrooms IS NULL OR bathrooms >= :bathrooms OR bathrooms IS NULL)
          AND (:strict_filters IS FALSE OR :parking_spaces IS NULL OR parking_spaces >= :parking_spaces OR parking_spaces IS NULL)
          AND embedding IS NOT NULL
        ORDER BY
          CASE
            WHEN :strict_filters IS FALSE AND :price_max IS NOT NULL THEN abs(price - :price_max)
            ELSE 0
          END ASC,
          embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """
    return list(
        db.execute(
            select(Property).from_statement(text(base_sql)),
            {
                "city": parsed_query.get("city") or "Cartagena",
                "operation": parsed_query.get("operation"),
                "require_location": bool(require_location and location_likes),
                "location_likes": location_likes or ["%%"],
                "strict_filters": strict,
                "property_type": parsed_query.get("property_type"),
                "price_min": parsed_query.get("price_min"),
                "price_max": parsed_query.get("price_max"),
                "bedrooms": parsed_query.get("bedrooms"),
                "bathrooms": parsed_query.get("bathrooms"),
                "parking_spaces": parsed_query.get("parking_spaces"),
                "embedding": embedding,
                "limit": limit,
            },
        ).scalars().all()
    )


def search_saved_properties_with_meta(db, parsed_query: dict, user_message: str, limit: int = 24) -> tuple[list[Property], dict]:
    embedding = to_pgvector_literal(generate_embedding(user_message))
    requested_zone = parsed_query.get("zone") or parsed_query.get("neighborhood") or parsed_query.get("original_zone")
    nearby_zones = nearby_neighborhoods(requested_zone) if requested_zone else []
    meta = {
        "exact_result_count": 0,
        "fallback_reason": None,
        "fallback_scope": None,
        "nearby_offer_zones": nearby_zones,
        "allow_nearby_followup": bool(requested_zone and nearby_zones),
        "original_zone": requested_zone,
    }
    if db.bind.dialect.name == "postgresql" and embedding:
        rows = _semantic_property_search(db, parsed_query, embedding, strict=True, require_location=True, limit=limit)
        if rows:
            meta["exact_result_count"] = len(rows)
            meta["fallback_scope"] = "exact"
            return rows, meta

        rows = _semantic_property_search(db, parsed_query, embedding, strict=False, require_location=True, limit=limit)
        if rows:
            meta["fallback_reason"] = "no_exact_match"
            meta["fallback_scope"] = "location_relaxed_filters"
            return rows, meta

        if parsed_query.get("location_match_scope") == "nearby":
            meta["fallback_reason"] = "no_exact_match"
            meta["fallback_scope"] = "nearby_only"
            return [], meta

        similar_query = _price_window_query(parsed_query)
        rows = _semantic_property_search(db, similar_query, embedding, strict=True, require_location=False, limit=limit)
        if rows:
            meta["fallback_reason"] = "no_exact_match"
            meta["fallback_scope"] = "city_same_type_similar_price"
            return rows, meta

        rows = _semantic_property_search(db, similar_query, embedding, strict=False, require_location=False, limit=limit)
        if rows:
            meta["fallback_reason"] = "no_exact_match"
            meta["fallback_scope"] = "city_similar_price"
            return rows, meta

    stmt = _property_filters(select(Property), parsed_query).order_by(Property.last_seen_at.desc()).limit(limit)
    rows = list(db.execute(stmt).scalars().all())
    if rows:
        meta["exact_result_count"] = len(rows)
        meta["fallback_scope"] = "exact"
        return rows, meta

    fallback_stmt = _property_filters(select(Property), parsed_query, strict=False).order_by(Property.last_seen_at.desc()).limit(limit)
    rows = list(db.execute(fallback_stmt).scalars().all())
    if rows:
        meta["fallback_reason"] = "no_exact_match"
        meta["fallback_scope"] = "location_relaxed_filters"
    return rows, meta


def search_saved_properties(db, parsed_query: dict, user_message: str, limit: int = 24) -> list[Property]:
    rows, _meta = search_saved_properties_with_meta(db, parsed_query, user_message, limit)
    return rows


def _active_source_count(db, city: str, source: str, operation: str) -> int:
    return int(
        db.execute(
            select(func.count(Property.id)).where(
                func.lower(Property.city) == city.lower(),
                Property.source == source,
                Property.operation == operation,
                Property.status == "active",
            )
        ).scalar()
        or 0
    )


def _should_mark_inactive(db, city: str, source: str, operation: str, seen_urls: set[str]) -> bool:
    if not seen_urls:
        return False
    active_count = _active_source_count(db, city, source, operation)
    if active_count == 0:
        return True
    minimum_safe_count = max(20, int(active_count * 0.8))
    if len(seen_urls) < minimum_safe_count:
        logger.warning(
            "Skipping inactive marking for %s %s %s: seen %s active %s",
            city,
            operation,
            source,
            len(seen_urls),
            active_count,
        )
        return False
    return True


def _inventory_zones_for_city(city: str) -> list[str]:
    if city.lower() == "cartagena":
        return sorted(set(NEIGHBORHOOD_ALIASES.values()))
    if city.lower() == "barranquilla":
        return list(BARRANQUILLA_NEIGHBORHOODS)
    return []


def _inventory_queries(city: str, operation: str) -> list[dict]:
    max_pages = int(os.getenv("SCRAPER_MAX_PAGES", "40"))
    zone_max_pages = int(os.getenv("SCRAPER_ZONE_MAX_PAGES", "3"))
    queries = [
        {
            "city": city,
            "operation": operation,
            "sources": list(ACTIVE_PROPERTY_SOURCES),
            "max_pages": max_pages,
        }
    ]
    for zone in _inventory_zones_for_city(city):
        queries.append(
            {
                "city": city,
                "zone": zone,
                "neighborhood": zone,
                "operation": operation,
                "sources": list(ACTIVE_PROPERTY_SOURCES),
                "max_pages": zone_max_pages,
            }
        )
    return queries


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

        search_query = db.get(SearchQuery, query_id)
        preset_query = (search_query.parsed_query_json if search_query else {}) or {}
        if preset_query.get("__preset"):
            parsed_query = {key: value for key, value in preset_query.items() if key != "__preset"}
            parser_used = "preset-followup"
        else:
            parsed_query, parser_used = parse_user_query(user_message)
        job.status = "searching_database"
        db.commit()

        _ensure_property_detail_columns(db)
        saved_results, search_meta = search_saved_properties_with_meta(db, parsed_query, user_message)
        parsed_query.update(search_meta)

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


@celery.task(name="app.tasks.scraping_tasks.refresh_property_inventory", soft_time_limit=21000, time_limit=21600)
def refresh_property_inventory(city: str | None = None, operation: str | None = None) -> dict:
    cities = (city,) if city else ("Cartagena", "Barranquilla")
    operations = (operation,) if operation else ("rent", "sale")
    sources = ("FincaRaiz", "Metrocuadrado")
    db = SessionLocal()
    summary = {"scraped": 0, "upserted": 0, "scopes": []}
    try:
        ensure_property_storage(db)
        for city in cities:
            for operation in operations:
                started_at = datetime.utcnow()
                seen_by_source = {source: set() for source in sources}
                scope_count = 0
                for query in _inventory_queries(city, operation):
                    raw_results = run_live_property_search(query)
                    normalized_results = _normalize_results_for_query(raw_results, query)
                    summary["scraped"] += len(raw_results)
                    scope_count += len(normalized_results)
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
                    if _should_mark_inactive(db, city, source, operation, seen_urls):
                        mark_missing_properties_inactive(
                            db,
                            city,
                            source,
                            operation,
                            seen_urls,
                            started_at,
                            missing_threshold=MISSING_INACTIVE_THRESHOLD,
                        )
                summary["scopes"].append({"city": city, "operation": operation, "count": scope_count})
                db.commit()
        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
