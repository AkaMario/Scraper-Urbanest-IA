CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    city VARCHAR(120),
    zone VARCHAR(120),
    neighborhood VARCHAR(120),
    property_type VARCHAR(80),
    price INTEGER NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    area_m2 NUMERIC(10,2),
    source VARCHAR(80) NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT,
    scraped_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

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
