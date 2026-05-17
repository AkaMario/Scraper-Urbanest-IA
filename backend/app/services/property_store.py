from datetime import datetime

from sqlalchemy import JSON, bindparam, inspect, text

from app.config import settings
from app.services.embeddings import build_embedding_text, generate_embedding, to_pgvector_literal


PROPERTY_COLUMNS = {
    "operation": "VARCHAR(40) NOT NULL DEFAULT 'rent'",
    "parking_spaces": "INTEGER",
    "stratum": "INTEGER",
    "features": "JSONB",
    "image_urls": "JSONB NOT NULL DEFAULT '[]'::jsonb",
    "raw_text": "TEXT",
    "raw_data": "JSONB",
    "status": "VARCHAR(30) NOT NULL DEFAULT 'active'",
    "first_seen_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    "last_seen_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    "updated_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
}


def ensure_property_storage(db) -> None:
    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        price_type = db.execute(
            text(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'properties' AND column_name = 'price'
                """
            )
        ).scalar()
        if price_type and price_type != "bigint":
            db.execute(text("ALTER TABLE properties ALTER COLUMN price TYPE BIGINT"))

    columns = {column["name"] for column in inspect(db.bind).get_columns("properties")}
    for name, definition in PROPERTY_COLUMNS.items():
        if name not in columns:
            column_definition = definition
            if dialect != "postgresql" and "JSONB" in column_definition:
                column_definition = column_definition.replace("JSONB", "JSON").replace("::jsonb", "")
            db.execute(text(f"ALTER TABLE properties ADD COLUMN {name} {column_definition}"))

    if dialect == "postgresql" and "embedding" not in columns:
        db.execute(text(f"ALTER TABLE properties ADD COLUMN embedding vector({settings.embeddings_dimensions})"))
    if dialect == "postgresql":
        duplicate_count = db.execute(
            text("SELECT COUNT(*) FROM (SELECT url FROM properties GROUP BY url HAVING COUNT(*) > 1) duplicates")
        ).scalar() or 0
        if duplicate_count == 0:
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_properties_url_unique ON properties (url)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_properties_city_status ON properties (city, status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_properties_operation ON properties (operation)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_properties_last_seen ON properties (last_seen_at)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_properties_embedding ON properties USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"))
        db.execute(text(
            """
            CREATE TABLE IF NOT EXISTS legal_knowledge_documents (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                embedding vector(768),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        ))
        legal_columns = {column["name"] for column in inspect(db.bind).get_columns("legal_knowledge_documents")}
        if "embedding" not in legal_columns:
            db.execute(text(f"ALTER TABLE legal_knowledge_documents ADD COLUMN embedding vector({settings.embeddings_dimensions})"))
        if "metadata" not in legal_columns:
            db.execute(text("ALTER TABLE legal_knowledge_documents ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}'::jsonb"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_legal_knowledge_embedding ON legal_knowledge_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"))
    db.commit()


def normalize_for_storage(item: dict) -> dict:
    image_urls = item.get("image_urls") or []
    if item.get("image_url") and item["image_url"] not in image_urls:
        image_urls = [item["image_url"], *image_urls]
    image_urls = [str(url) for url in image_urls if url]
    raw_text = item.get("raw_text") or " ".join(
        str(item.get(field) or "") for field in ("title", "description", "city", "zone", "neighborhood")
    ).strip()
    now = datetime.utcnow()
    return {
        **item,
        "title": item.get("title") or "Inmueble",
        "description": item.get("description"),
        "city": item.get("city") or "Cartagena",
        "zone": item.get("zone"),
        "neighborhood": item.get("neighborhood"),
        "property_type": item.get("property_type"),
        "operation": item.get("operation") or "rent",
        "price": int(item.get("price") or 0),
        "bedrooms": item.get("bedrooms"),
        "bathrooms": item.get("bathrooms"),
        "parking_spaces": item.get("parking_spaces"),
        "stratum": item.get("stratum"),
        "area_m2": item.get("area_m2"),
        "features": item.get("features") or [],
        "source": item.get("source") or "Unknown",
        "url": item.get("url"),
        "image_urls": image_urls[:24],
        "image_url": item.get("image_url") or (image_urls[0] if image_urls else None),
        "raw_text": raw_text,
        "raw_data": item.get("raw_data") or item,
        "status": "active",
        "last_seen_at": now,
        "scraped_at": item.get("scraped_at") or now,
        "updated_at": now,
    }


def upsert_property(db, item: dict) -> None:
    payload = normalize_for_storage(item)
    embedding = to_pgvector_literal(generate_embedding(build_embedding_text(payload)))
    payload["embedding"] = embedding
    existing_id = db.execute(text("SELECT id FROM properties WHERE url = :url ORDER BY id LIMIT 1"), {"url": payload["url"]}).scalar()
    if existing_id:
        stmt = text(
            """
            UPDATE properties SET
                title = :title,
                description = :description,
                city = :city,
                zone = :zone,
                neighborhood = :neighborhood,
                property_type = :property_type,
                operation = :operation,
                price = :price,
                bedrooms = :bedrooms,
                bathrooms = :bathrooms,
                parking_spaces = :parking_spaces,
                stratum = :stratum,
                area_m2 = :area_m2,
                features = :features,
                source = :source,
                image_url = :image_url,
                image_urls = :image_urls,
                raw_text = :raw_text,
                raw_data = :raw_data,
                status = 'active',
                last_seen_at = :last_seen_at,
                scraped_at = :scraped_at,
                updated_at = :updated_at,
                embedding = COALESCE(CAST(:embedding AS vector), embedding)
            WHERE id = :id
            """
        ).bindparams(
            bindparam("features", type_=JSON),
            bindparam("image_urls", type_=JSON),
            bindparam("raw_data", type_=JSON),
        )
        db.execute(stmt, {**payload, "id": existing_id})
        return

    stmt = text(
        """
            INSERT INTO properties (
                title, description, city, zone, neighborhood, property_type, operation,
                price, bedrooms, bathrooms, parking_spaces, stratum, area_m2, features,
                source, url, image_url, image_urls, raw_text, raw_data, status,
                first_seen_at, last_seen_at, scraped_at, created_at, updated_at, embedding
            ) VALUES (
                :title, :description, :city, :zone, :neighborhood, :property_type, :operation,
                :price, :bedrooms, :bathrooms, :parking_spaces, :stratum, :area_m2, :features,
                :source, :url, :image_url, :image_urls, :raw_text, :raw_data, :status,
                NOW(), :last_seen_at, :scraped_at, NOW(), :updated_at, CAST(:embedding AS vector)
            )
        """
    ).bindparams(
        bindparam("features", type_=JSON),
        bindparam("image_urls", type_=JSON),
        bindparam("raw_data", type_=JSON),
    )
    db.execute(stmt, payload)


def mark_missing_properties_inactive(db, city: str, source: str, operation: str, seen_urls: set[str], started_at: datetime) -> None:
    if not seen_urls:
        return
    db.execute(
        text(
            """
            UPDATE properties
            SET status = 'inactive', updated_at = NOW()
            WHERE lower(city) = lower(:city)
              AND source = :source
              AND operation = :operation
              AND status = 'active'
              AND last_seen_at < :started_at
              AND NOT (url = ANY(:seen_urls))
            """
        ),
        {"city": city, "source": source, "operation": operation, "seen_urls": list(seen_urls), "started_at": started_at},
    )
