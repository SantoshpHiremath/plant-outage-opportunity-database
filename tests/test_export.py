import csv
import io
import os
import tempfile

from src.schema import create_connection
from src.repository import insert_operator, insert_plant, insert_outage_event, insert_service_category, create_scored_opportunity
from src.export import export_opportunities_csv, export_opportunities_csv_to_file, OPPORTUNITY_EXPORT_QUERY


def seed_one_opportunity(conn):
    operator_id = insert_operator(conn, "EDF", "France", True)
    plant_id = insert_plant(conn, "Gravelines", "France", "PWR", 900, 1980, operator_id)
    outage_id = insert_outage_event(conn, plant_id, "Refueling", "2027-03-01", 30)
    category_id = insert_service_category(conn, "Steam Generator Inspection", 500_000)
    return create_scored_opportunity(conn, outage_id, category_id, 600_000, 200)


class TestExportOpportunitiesCsv:
    def test_export_includes_a_header_row(self):
        conn = create_connection()
        seed_one_opportunity(conn)
        csv_text = export_opportunities_csv(conn)
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader)
        assert "opportunity_id" in header
        assert "priority_score" in header
        assert "operator_name" in header

    def test_export_includes_the_seeded_row_with_correct_values(self):
        conn = create_connection()
        seed_one_opportunity(conn)
        csv_text = export_opportunities_csv(conn)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["operator_name"] == "EDF"
        assert rows[0]["plant_name"] == "Gravelines"
        assert rows[0]["reactor_type"] == "PWR"

    def test_export_is_ordered_by_priority_score_descending(self):
        conn = create_connection()
        operator_a = insert_operator(conn, "Low Priority Co", "Germany", False)
        operator_b = insert_operator(conn, "High Priority Co", "France", True)
        plant_a = insert_plant(conn, "Plant A", "Germany", "BWR", 800, 1990, operator_a)
        plant_b = insert_plant(conn, "Plant B", "France", "PWR", 1300, 1985, operator_b)
        outage_a = insert_outage_event(conn, plant_a, "Unplanned", "2026-09-01", 10)
        outage_b = insert_outage_event(conn, plant_b, "Refueling", "2027-06-01", 30)
        category_id = insert_service_category(conn, "Generic Service", 500_000)

        create_scored_opportunity(conn, outage_a, category_id, 100_000, 5)   # low priority: new customer, tiny lead time
        create_scored_opportunity(conn, outage_b, category_id, 800_000, 250)  # high priority: existing customer, good lead time

        csv_text = export_opportunities_csv(conn)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)

        scores = [float(row["priority_score"]) for row in rows]
        assert scores == sorted(scores, reverse=True)
        assert rows[0]["operator_name"] == "High Priority Co"

    def test_export_with_no_opportunities_still_produces_a_valid_header_only_csv(self):
        conn = create_connection()
        csv_text = export_opportunities_csv(conn)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 1  # header only, no data rows


class TestExportOpportunitiesCsvToFile:
    def test_writes_a_real_file_and_returns_the_row_count(self):
        conn = create_connection()
        seed_one_opportunity(conn)

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "export.csv")
            row_count = export_opportunities_csv_to_file(conn, file_path)

            assert row_count == 1
            assert os.path.exists(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "EDF" in content
            assert "Gravelines" in content
