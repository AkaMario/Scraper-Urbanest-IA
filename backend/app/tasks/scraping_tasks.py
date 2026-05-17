from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import and_, func, inspect, or_, select, text

from app.database import SessionLocal
from app.models import Property, ScrapingJob, SearchQuery
from app.services.cartagena_locations import location_search_terms, nearby_neighborhoods
from app.services.property_analyzer import analyze_properties
from app.services.query_parser import parse_user_query
from scraper.normalizer import normalize_property, property_matches_query, run_property_search

from .celery_app import celery


ACTIVE_PROPERTY_SOURCES = ("FincaRaiz", "Metrocuadrado")


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
    columns = {column["name"] for column in inspect(db.bind).get_columns("properties")}
    if "features" in columns:
        return

    dialect = db.bind.dialect.name
    column_type = "JSON" if dialect != "sqlite" else "TEXT"
    db.execute(text(f"ALTER TABLE properties ADD COLUMN features {column_type}"))
    db.commit()


def _normalize_results_for_query(raw_results: list[dict], parsed_query: dict) -> list[dict]:
    return [
        normalized
        for normalized in (normalize_property(item, parsed_query) for item in raw_results)
        if property_matches_query(normalized, parsed_query)
    ]


def _run_search_scope(parsed_query: dict) -> list[dict]:
    return _normalize_results_for_query(run_property_search(parsed_query), parsed_query)


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
        job.status = "scraping"
        db.commit()

        normalized_results = _search_with_nearby_fallback(parsed_query)

        search_query = db.get(SearchQuery, query_id)
        if search_query:
            search_query.parsed_query_json = parsed_query
            db.commit()

        _ensure_property_detail_columns(db)
        for item in normalized_results:
            db.add(Property(**item))

        job.status = "completed"
        job.finished_at = datetime.utcnow()
        db.commit()

        analysis = analyze_properties(normalized_results)
        return {
            "job_id": job_id,
            "parser_used": parser_used,
            "parsed_query": parsed_query,
            "results": normalized_results,
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
