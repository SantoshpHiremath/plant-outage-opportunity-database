import pytest

from src.schema import create_connection
from src.repository import (
    insert_operator, insert_plant, insert_outage_event, insert_service_category,
    get_operator_fleet_size, create_scored_opportunity,
)


@pytest.fixture
def conn():
    return create_connection()


@pytest.fixture
def base_ids(conn):
    operator_id = insert_operator(conn, "EDF", "France", True, "Existing framework customer")
    plant_id = insert_plant(conn, "Gravelines", "France", "PWR", 900, 1980, operator_id)
    outage_id = insert_outage_event(conn, plant_id, "Refueling", "2027-03-01", 30, "Routine refueling")
    category_id = insert_service_category(conn, "Steam Generator Inspection", 500_000)
    return {
        "operator_id": operator_id,
        "plant_id": plant_id,
        "outage_id": outage_id,
        "category_id": category_id,
    }


class TestInserts:
    def test_insert_operator_returns_a_positive_id(self, conn):
        operator_id = insert_operator(conn, "Uniper", "Germany", False)
        assert operator_id > 0

    def test_insert_plant_links_to_its_operator(self, conn):
        operator_id = insert_operator(conn, "Uniper", "Germany", False)
        plant_id = insert_plant(conn, "Test Plant", "Germany", "PWR", 1000, 1990, operator_id)
        row = conn.execute("SELECT operator_id FROM plants WHERE plant_id = ?", (plant_id,)).fetchone()
        assert row[0] == operator_id

    def test_get_operator_fleet_size_counts_only_that_operators_plants(self, conn):
        operator_a = insert_operator(conn, "Operator A", "France", True)
        operator_b = insert_operator(conn, "Operator B", "Germany", False)
        insert_plant(conn, "Plant A1", "France", "PWR", 900, 1980, operator_a)
        insert_plant(conn, "Plant A2", "France", "PWR", 900, 1985, operator_a)
        insert_plant(conn, "Plant B1", "Germany", "BWR", 1000, 1990, operator_b)

        assert get_operator_fleet_size(conn, operator_a) == 2
        assert get_operator_fleet_size(conn, operator_b) == 1


class TestCreateScoredOpportunity:
    def test_creates_an_opportunity_with_a_computed_score_and_tier(self, conn, base_ids):
        opportunity_id = create_scored_opportunity(
            conn, base_ids["outage_id"], base_ids["category_id"],
            estimated_value_eur=600_000, days_until_outage=200,
        )
        row = conn.execute(
            "SELECT priority_score, priority_tier, status FROM opportunities WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()
        assert row[0] is not None and row[0] > 0
        assert row[1] in {"High", "Medium", "Low"}
        assert row[2] == "Identified"

    def test_existing_customer_opportunity_scores_higher_than_new_customer_all_else_equal(self, conn):
        existing_op = insert_operator(conn, "Existing Co", "France", True)
        new_op = insert_operator(conn, "New Co", "Germany", False)
        plant_existing = insert_plant(conn, "Plant Existing", "France", "PWR", 900, 1980, existing_op)
        plant_new = insert_plant(conn, "Plant New", "Germany", "PWR", 900, 1980, new_op)
        outage_existing = insert_outage_event(conn, plant_existing, "Refueling", "2027-01-01", 30)
        outage_new = insert_outage_event(conn, plant_new, "Refueling", "2027-01-01", 30)
        category_id = insert_service_category(conn, "Generic Service", 500_000)

        opp_existing = create_scored_opportunity(conn, outage_existing, category_id, 500_000, 200)
        opp_new = create_scored_opportunity(conn, outage_new, category_id, 500_000, 200)

        score_existing = conn.execute("SELECT priority_score FROM opportunities WHERE opportunity_id = ?", (opp_existing,)).fetchone()[0]
        score_new = conn.execute("SELECT priority_score FROM opportunities WHERE opportunity_id = ?", (opp_new,)).fetchone()[0]

        assert score_existing > score_new

    def test_raises_for_a_nonexistent_outage_id(self, conn, base_ids):
        with pytest.raises(ValueError, match="outage_event"):
            create_scored_opportunity(conn, 9999, base_ids["category_id"], 500_000, 200)

    def test_raises_for_a_nonexistent_service_category_id(self, conn, base_ids):
        with pytest.raises(ValueError, match="service_category"):
            create_scored_opportunity(conn, base_ids["outage_id"], 9999, 500_000, 200)

    def test_identified_by_field_is_stored_correctly(self, conn, base_ids):
        opportunity_id = create_scored_opportunity(
            conn, base_ids["outage_id"], base_ids["category_id"],
            500_000, 200, identified_by="ai_assisted",
        )
        row = conn.execute("SELECT identified_by FROM opportunities WHERE opportunity_id = ?", (opportunity_id,)).fetchone()
        assert row[0] == "ai_assisted"
