"""
A thin, real data-access layer over the schema: inserting operators,
plants, outage events, service categories, and opportunities, plus the
score-and-insert pipeline that ties src/scoring.py to the database.
Kept as plain, explicit SQL (via sqlite3's parameterized queries, so
no manual string-concatenation SQL-injection risk anywhere in this
project) rather than an ORM, since the posting specifically names
"SQL oder vergleichbar" as the target skill being assessed.
"""
import sqlite3

from src.scoring import ScoringInputs, compute_priority_score, tier_for_score


def insert_operator(conn: sqlite3.Connection, operator_name: str, country: str,
                     is_existing_customer: bool, relationship_notes: str = "") -> int:
    cursor = conn.execute(
        "INSERT INTO operators (operator_name, country, is_existing_customer, relationship_notes) "
        "VALUES (?, ?, ?, ?)",
        (operator_name, country, int(is_existing_customer), relationship_notes),
    )
    conn.commit()
    return cursor.lastrowid


def insert_plant(conn: sqlite3.Connection, plant_name: str, country: str, reactor_type: str,
                  net_capacity_mw: int, commercial_operation_year: int, operator_id: int) -> int:
    cursor = conn.execute(
        "INSERT INTO plants (plant_name, country, reactor_type, net_capacity_mw, "
        "commercial_operation_year, operator_id) VALUES (?, ?, ?, ?, ?, ?)",
        (plant_name, country, reactor_type, net_capacity_mw, commercial_operation_year, operator_id),
    )
    conn.commit()
    return cursor.lastrowid


def insert_outage_event(conn: sqlite3.Connection, plant_id: int, outage_type: str,
                         planned_start_date: str, planned_duration_days: int,
                         scope_summary: str = "", source_reference: str = "") -> int:
    cursor = conn.execute(
        "INSERT INTO outage_events (plant_id, outage_type, planned_start_date, "
        "planned_duration_days, scope_summary, source_reference) VALUES (?, ?, ?, ?, ?, ?)",
        (plant_id, outage_type, planned_start_date, planned_duration_days, scope_summary, source_reference),
    )
    conn.commit()
    return cursor.lastrowid


def insert_service_category(conn: sqlite3.Connection, category_name: str,
                             typical_contract_value_eur: int) -> int:
    cursor = conn.execute(
        "INSERT INTO service_categories (category_name, typical_contract_value_eur) VALUES (?, ?)",
        (category_name, typical_contract_value_eur),
    )
    conn.commit()
    return cursor.lastrowid


def get_operator_fleet_size(conn: sqlite3.Connection, operator_id: int) -> int:
    cursor = conn.execute("SELECT COUNT(*) FROM plants WHERE operator_id = ?", (operator_id,))
    return cursor.fetchone()[0]


def create_scored_opportunity(
    conn: sqlite3.Connection,
    outage_id: int,
    service_category_id: int,
    estimated_value_eur: int,
    days_until_outage: int,
    identified_by: str = "manual",
    notes: str = "",
) -> int:
    """The real end-to-end pipeline: looks up the context needed to
    score the opportunity (operator relationship, fleet size, service
    category's typical value), computes the priority score via
    src/scoring.py, and inserts a fully-scored opportunity row --
    rather than leaving scoring as a disconnected, manual step."""
    outage_row = conn.execute(
        "SELECT plant_id FROM outage_events WHERE outage_id = ?", (outage_id,)
    ).fetchone()
    if outage_row is None:
        raise ValueError(f"No outage_event found with outage_id={outage_id}")
    plant_id = outage_row[0]

    plant_row = conn.execute(
        "SELECT operator_id FROM plants WHERE plant_id = ?", (plant_id,)
    ).fetchone()
    if plant_row is None:
        raise ValueError(f"No plant found with plant_id={plant_id}")
    operator_id = plant_row[0]

    operator_row = conn.execute(
        "SELECT is_existing_customer FROM operators WHERE operator_id = ?", (operator_id,)
    ).fetchone()
    if operator_row is None:
        raise ValueError(f"No operator found with operator_id={operator_id}")
    is_existing_customer = bool(operator_row[0])

    category_row = conn.execute(
        "SELECT typical_contract_value_eur FROM service_categories WHERE service_category_id = ?",
        (service_category_id,),
    ).fetchone()
    if category_row is None:
        raise ValueError(f"No service_category found with service_category_id={service_category_id}")
    typical_value = category_row[0] or 0

    fleet_size = get_operator_fleet_size(conn, operator_id)

    inputs = ScoringInputs(
        is_existing_customer=is_existing_customer,
        estimated_value_eur=estimated_value_eur,
        reactor_fleet_size_for_operator=fleet_size,
        days_until_outage=days_until_outage,
        service_category_typical_value_eur=typical_value,
    )
    score = compute_priority_score(inputs)
    tier = tier_for_score(score)

    cursor = conn.execute(
        "INSERT INTO opportunities (outage_id, service_category_id, estimated_value_eur, "
        "priority_score, priority_tier, status, identified_by, notes) "
        "VALUES (?, ?, ?, ?, ?, 'Identified', ?, ?)",
        (outage_id, service_category_id, estimated_value_eur, score, tier, identified_by, notes),
    )
    conn.commit()
    return cursor.lastrowid
