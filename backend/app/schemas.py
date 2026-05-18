from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    properties: list["PropertyContext"] = Field(default_factory=list)
    parsed_query: "ParsedQuery | None" = None
    analysis: "AnalysisContext | None" = None


class ParsedQuery(BaseModel):
    city: str = "Cartagena"
    zone: str | None = None
    neighborhood: str | None = None
    property_type: str | None = None
    operation: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking_spaces: int | None = None
    keywords: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    accepted_zones: list[str] = Field(default_factory=list)
    nearby_zones_checked: list[str] = Field(default_factory=list)
    location_match_scope: str | None = None
    exact_result_count: int | None = None
    fallback_reason: str | None = None
    fallback_scope: str | None = None
    nearby_offer_zones: list[str] = Field(default_factory=list)
    allow_nearby_followup: bool = False
    original_zone: str | None = None


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    city: str | None = None
    zone: str | None = None
    neighborhood: str | None = None
    property_type: str | None = None
    operation: str = "rent"
    price: int
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking_spaces: int | None = None
    stratum: int | None = None
    area_m2: float | None = None
    features: list[str] | None = Field(default_factory=list)
    source: str
    url: str
    image_url: str | None = None
    image_urls: list[str] | None = Field(default_factory=list)
    raw_text: str | None = None
    status: str = "active"
    missing_count: int = 0
    last_seen_at: datetime | None = None
    scraped_at: datetime


class PropertyContext(BaseModel):
    title: str
    description: str | None = None
    city: str | None = None
    zone: str | None = None
    neighborhood: str | None = None
    property_type: str | None = None
    operation: str | None = None
    price: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking_spaces: int | None = None
    stratum: int | None = None
    area_m2: float | None = None
    features: list[str] | None = Field(default_factory=list)
    source: str | None = None
    url: str | None = None
    image_url: str | None = None
    image_urls: list[str] | None = Field(default_factory=list)


class AnalysisOut(BaseModel):
    total_results: int
    average_price: float | None = None
    min_price: int | None = None
    max_price: int | None = None
    below_average_count: int = 0
    opportunities: list[PropertyOut] = Field(default_factory=list)


class AnalysisContext(BaseModel):
    total_results: int | None = None
    average_price: float | None = None
    min_price: int | None = None
    max_price: int | None = None
    below_average_count: int = 0
    opportunities: list[PropertyContext] = Field(default_factory=list)


class JobOut(BaseModel):
    id: int
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    reply: str | None = None
    parsed_query: ParsedQuery | None = None
    results: list[PropertyOut] = Field(default_factory=list)
    analysis: AnalysisOut | None = None


class ChatResponse(BaseModel):
    reply: str
    parsed_query: ParsedQuery | None = None
    results: list[PropertyOut] = Field(default_factory=list)
    job_id: int | None = None
