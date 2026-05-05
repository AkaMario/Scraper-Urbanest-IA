from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Property
from app.schemas import PropertyOut


router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.get("", response_model=list[PropertyOut])
def list_properties(db: Session = Depends(get_db)):
    stmt = select(Property).order_by(Property.scraped_at.desc()).limit(100)
    return list(db.execute(stmt).scalars().all())


@router.get("/search", response_model=list[PropertyOut])
def search_properties(
    city: str | None = None,
    zone: str | None = None,
    price_min: int | None = Query(default=None, ge=0),
    price_max: int | None = Query(default=None, ge=0),
    bedrooms: int | None = Query(default=None, ge=0),
    source: str | None = None,
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
    return list(db.execute(stmt.order_by(Property.scraped_at.desc()).limit(100)).scalars().all())
