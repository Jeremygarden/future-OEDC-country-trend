-- Country Stats Dashboard Database Schema
-- Tracks macroeconomic data for US, China, Japan, Australia, Canada

CREATE TABLE IF NOT EXISTS countries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    iso2        TEXT NOT NULL UNIQUE,   -- 2-letter ISO code (US, CN, JP, AU, CA)
    iso3        TEXT NOT NULL UNIQUE,   -- 3-letter ISO code (USA, CHN, JPN, AUS, CAN)
    name        TEXT NOT NULL,
    region      TEXT,                   -- e.g. "North America", "East Asia"
    income_group TEXT,                  -- World Bank income classification
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    api_type    TEXT NOT NULL,          -- 'worldbank', 'oecd', 'manual'
    description TEXT,
    last_sync   TIMESTAMP,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS indicators (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL,          -- e.g. "NY.GDP.MKTP.CD"
    name        TEXT NOT NULL,
    description TEXT,
    unit        TEXT,                   -- e.g. "USD", "%", "persons"
    category    TEXT,                   -- e.g. "GDP", "Employment", "Trade"
    source_id   INTEGER REFERENCES data_sources(id),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, source_id)
);

CREATE TABLE IF NOT EXISTS data_points (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id   INTEGER NOT NULL REFERENCES countries(id),
    indicator_id INTEGER NOT NULL REFERENCES indicators(id),
    year         INTEGER NOT NULL,
    value        REAL,
    source_id    INTEGER REFERENCES data_sources(id),
    fetched_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_id, indicator_id, year)
);

CREATE TABLE IF NOT EXISTS etl_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       INTEGER REFERENCES data_sources(id),
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at     TIMESTAMP,
    status          TEXT NOT NULL DEFAULT 'running', -- 'running','success','error'
    records_fetched INTEGER DEFAULT 0,
    records_upserted INTEGER DEFAULT 0,
    error_msg       TEXT
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_data_points_country ON data_points(country_id);
CREATE INDEX IF NOT EXISTS idx_data_points_indicator ON data_points(indicator_id);
CREATE INDEX IF NOT EXISTS idx_data_points_year ON data_points(year);
CREATE INDEX IF NOT EXISTS idx_data_points_lookup ON data_points(country_id, indicator_id, year);
