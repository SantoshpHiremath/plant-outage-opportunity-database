import sqlite3

import pytest

from src.schema import create_connection


class TestSchema:
    def test_creates_all_expected_tables(self):
        conn = create_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row[0] for row in cursor.fetchall()}
        expected = {"plants", "operators", "outage_events", "service_categories", "opportunities"}
        assert expected.issubset(table_names)

    def test_foreign_keys_are_enforced(self):
        conn = create_connection()
        with pytest.raises(sqlite3.IntegrityError):
            # plant references a non-existent operator_id
            conn.execute(
                "INSERT INTO plants (plant_name, country, reactor_type, operator_id) "
                "VALUES ('Ghost Plant', 'Nowhere', 'PWR', 9999)"
            )
            conn.commit()

    def test_operator_name_must_be_unique(self):
        conn = create_connection()
        conn.execute("INSERT INTO operators (operator_name, country, is_existing_customer) VALUES ('EDF', 'France', 1)")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO operators (operator_name, country, is_existing_customer) VALUES ('EDF', 'France', 0)")
            conn.commit()

    def test_priority_index_exists(self):
        conn = create_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = {row[0] for row in cursor.fetchall()}
        assert "idx_opportunities_priority" in index_names

    def test_schema_is_idempotent_to_apply_twice(self):
        # create_connection uses CREATE TABLE IF NOT EXISTS -- applying
        # the schema twice against the same connection must not raise.
        conn = create_connection()
        conn.executescript(__import__("src.schema", fromlist=["SCHEMA_SQL"]).SCHEMA_SQL)
