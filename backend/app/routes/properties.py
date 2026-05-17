from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Property
from app.schemas import PropertyOut


router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.get("", response_model=list[PropertyOut])
def list_properties(
    city: str | None = None,
    status: str | None = None,
    operation: str | None = None,
    source: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Property)
    if city:
        stmt = stmt.where(Property.city.ilike(f"%{city}%"))
    if status:
        stmt = stmt.where(Property.status == status)
    if operation:
        stmt = stmt.where(Property.operation == operation)
    if source:
        stmt = stmt.where(Property.source.ilike(f"%{source}%"))
    stmt = stmt.order_by(Property.last_seen_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/stats")
def property_stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Property.city, Property.operation, Property.status, func.count(Property.id))
        .group_by(Property.city, Property.operation, Property.status)
        .order_by(Property.city, Property.operation, Property.status)
    ).all()
    return [
        {"city": city, "operation": operation, "status": status, "count": count}
        for city, operation, status, count in rows
    ]


@router.get("/search", response_model=list[PropertyOut])
def search_properties(
    city: str | None = None,
    zone: str | None = None,
    price_min: int | None = Query(default=None, ge=0),
    price_max: int | None = Query(default=None, ge=0),
    bedrooms: int | None = Query(default=None, ge=0),
    source: str | None = None,
    operation: str | None = None,
    status: str = "active",
    db: Session = Depends(get_db),
):
    stmt = select(Property)
    if city:
        stmt = stmt.where(Property.city.ilike(f"%{city}%"))
    if zone:
        stmt = stmt.where(Property.zone.ilike(f"%{zone}%"))
    if price_min is not None:
        stmt = stmt.where(Property.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Property.price <= price_max)
    if bedrooms is not None:
        stmt = stmt.where(Property.bedrooms == bedrooms)
    if source:
        stmt = stmt.where(Property.source.ilike(f"%{source}%"))
    if operation:
        stmt = stmt.where(Property.operation == operation)
    if status:
        stmt = stmt.where(Property.status == status)
    return list(db.execute(stmt.order_by(Property.scraped_at.desc()).limit(100)).scalars().all())
