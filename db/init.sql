CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    city VARCHAR(120),
    zone VARCHAR(120),
    neighborhood VARCHAR(120),
    property_type VARCHAR(80),
    operation VARCHAR(40) NOT NULL DEFAULT 'rent',
    price BIGINT NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    parking_spaces INTEGER,
    stratum INTEGER,
    area_m2 NUMERIC(10,2),
    features JSONB,
    source VARCHAR(80) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    image_url TEXT,
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_text TEXT,
    raw_data JSONB,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    missing_count INTEGER NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    embedding vector(768),
    scraped_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_properties_city_status ON properties (city, status);
CREATE INDEX IF NOT EXISTS idx_properties_operation ON properties (operation);
CREATE INDEX IF NOT EXISTS idx_properties_source ON properties (source);
CREATE INDEX IF NOT EXISTS idx_properties_last_seen ON properties (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_properties_embedding ON properties USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS legal_knowledge_documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(768),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_legal_knowledge_embedding ON legal_knowledge_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS search_queries (
    id SERIAL PRIMARY KEY,
    user_message TEXT NOT NULL,
    parsed_query_json JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scraping_jobs (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES search_queries(id) ON DELETE CASCADE,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT
);
