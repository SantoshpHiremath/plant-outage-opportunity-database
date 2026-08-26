"""
Real SQLite schema for a nuclear-plant-outage-service business
opportunity database: plants, customers/operators, outage events, and
opportunities scored against them. Built specifically for Framatome's
"Werkstudent zur Erstellung einer Datenbank" posting, which asks for a
SQL (or comparable) database for the "preliminary identification and
evaluation of business opportunities in the plant outage revision
service" domain, designed for extension and automated exports.

Every table is designed to be extended (see README's "designed for
extension" section) rather than a one-off flat table -- the posting
explicitly asks for "Programmierung in einer Art, dass
Erweiterungsmoeglichkeiten vorgesehen werden."
"""
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS plants (
    plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_name TEXT NOT NULL,
    country TEXT NOT NULL,
    reactor_type TEXT NOT NULL,          -- e.g. PWR, BWR, VVER, CANDU
    net_capacity_mw INTEGER,
    commercial_operation_year INTEGER,
    operator_id INTEGER NOT NULL,
    FOREIGN KEY (operator_id) REFERENCES operators(operator_id)
);

CREATE TABLE IF NOT EXISTS operators (
    operator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_name TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    is_existing_customer INTEGER NOT NULL DEFAULT 0,  -- boolean: 0/1
    relationship_notes TEXT
);

CREATE TABLE IF NOT EXISTS outage_events (
    outage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_id INTEGER NOT NULL,
    outage_type TEXT NOT NULL,           -- e.g. Refueling, Major Overhaul, Unplanned
    planned_start_date TEXT,             -- ISO 8601 date string
    planned_duration_days INTEGER,
    scope_summary TEXT,
    source_reference TEXT,               -- where this outage information came from (extensible free-text)
    FOREIGN KEY (plant_id) REFERENCES plants(plant_id)
);

CREATE TABLE IF NOT EXISTS service_categories (
    service_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,   -- e.g. "Steam Generator Inspection", "RPV Head Replacement"
    typical_contract_value_eur INTEGER
);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    outage_id INTEGER NOT NULL,
    service_category_id INTEGER NOT NULL,
    estimated_value_eur INTEGER,
    priority_score REAL,                  -- computed by src/scoring.py, see README
    priority_tier TEXT,                   -- High / Medium / Low, derived from priority_score
    status TEXT NOT NULL DEFAULT 'Identified',  -- Identified / Qualified / Pursuing / Won / Lost / Discarded
    identified_by TEXT NOT NULL DEFAULT 'manual',  -- 'manual' or 'ai_assisted' -- see README for what this means
    notes TEXT,
    FOREIGN KEY (outage_id) REFERENCES outage_events(outage_id),
    FOREIGN KEY (service_category_id) REFERENCES service_categories(service_category_id)
);

CREATE INDEX IF NOT EXISTS idx_opportunities_priority ON opportunities(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_outage_events_plant ON outage_events(plant_id);
CREATE INDEX IF NOT EXISTS idx_plants_operator ON plants(operator_id);
"""


def create_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    """Creates (or opens) the database at db_path and ensures the full
    schema exists. Using :memory: by default keeps tests fast and
    hermetic; a real file path is used for the persistent demo
    database (see run_demo.py)."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
