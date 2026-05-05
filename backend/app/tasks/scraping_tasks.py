from datetime import datetime

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Property, ScrapingJob, SearchQuery
from app.services.property_analyzer import analyze_properties
from app.services.query_parser import parse_user_query
from scraper.normalizer import normalize_property, property_matches_query, run_property_search

from .celery_app import celery


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
        search_query = db.get(SearchQuery, query_id)
        if search_query:
            search_query.parsed_query_json = parsed_query
            db.commit()

        job.status = "scraping"
        db.commit()

        raw_results = run_property_search(parsed_query)
        normalized_results = [
            normalized
            for normalized in (normalize_property(item, parsed_query) for item in raw_results)
            if property_matches_query(normalized, parsed_query)
        ]

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
    if parsed_query.get("zone"):
        stmt = stmt.where(func.lower(Property.zone) == parsed_query["zone"].lower())
    if parsed_query.get("property_type"):
        stmt = stmt.where(func.lower(Property.property_type) == parsed_query["property_type"].lower())
    stmt = stmt.where(~Property.source.ilike("%Mock%"))
    if job.started_at:
        stmt = stmt.where(Property.scraped_at >= job.started_at)
    if job.finished_at:
        stmt = stmt.where(Property.scraped_at <= job.finished_at)
    return list(db.execute(stmt.order_by(Property.scraped_at.desc())).scalars().all())
