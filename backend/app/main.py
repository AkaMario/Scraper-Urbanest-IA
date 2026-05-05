from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn

from app.database import Base, engine, get_db
from app.models import ScrapingJob, SearchQuery
from app.ollama_client import build_search_reply
from app.routes.chat import router as chat_router
from app.routes.properties import router as properties_router
from app.schemas import AnalysisOut, JobOut, ParsedQuery, PropertyOut
from app.services.property_analyzer import analyze_properties
from app.tasks.scraping_tasks import get_job_results


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Urbanest IA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(properties_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ScrapingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    query = db.get(SearchQuery, job.query_id)
    raw_query = (query.parsed_query_json if query else {}) or {}
    parsed_query = ParsedQuery(**raw_query) if raw_query else None
    results = get_job_results(db, job_id) if job.status == "completed" else []
    serialized_results = [PropertyOut.model_validate(item) for item in results]
    analysis = None
    reply = None
    analysis_payload = None
    if serialized_results:
        analysis_payload = analyze_properties([item.model_dump() for item in serialized_results])
        opportunities_payload = analysis_payload.get("opportunities", [])
        analysis = AnalysisOut(
            **{
                key: value
                for key, value in analysis_payload.items()
                if key != "opportunities"
            },
            opportunities=[
                PropertyOut.model_validate(item)
                for item in opportunities_payload
            ],
        )
    if job.status == "completed":
        reply = build_search_reply(
            message=query.user_message if query else None,
            properties=[item.model_dump() for item in serialized_results],
            parsed_query=raw_query or None,
            analysis=analysis_payload,
        )

    return JobOut(
        id=job.id,
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_message=job.error_message,
        reply=reply,
        parsed_query=parsed_query,
        results=serialized_results,
        analysis=analysis,
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
