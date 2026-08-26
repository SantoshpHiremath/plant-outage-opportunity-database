"""
End-to-end demonstration: seeds a small, realistic set of operators,
plants, and service categories; uses the AI-assisted (mock) extractor
to turn unstructured outage-announcement text into candidate
opportunities; scores and inserts them; and produces a real CSV
export -- the full pipeline this database is designed to support, run
against real SQLite, not just described.
"""
import os

from src.schema import create_connection
from src.repository import (
    insert_operator, insert_plant, insert_outage_event, insert_service_category,
    create_scored_opportunity,
)
from src.ai_extraction import MockExtractionClient
from src.export import export_opportunities_csv_to_file

DB_PATH = os.path.join(os.path.dirname(__file__), "output", "opportunities_demo.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "output", "opportunities_export.csv")

# Illustrative outage-announcement snippets in the style this database
# is meant to process -- not real news articles, but realistic in
# phrasing and structure.
SAMPLE_ANNOUNCEMENTS = [
    "Gravelines Nuclear Power Plant will begin a planned refueling outage "
    "in March 2027, with inspection of the steam generator tubing expected "
    "to be part of the scope.",
    "Doel Nuclear Power Plant, a PWR facility in Belgium, has scheduled a "
    "major overhaul outage for late 2027 to support long-term operation.",
    "An unplanned shutdown was reported at a BWR facility following a "
    "routine inspection; scope and duration are still being determined.",
]


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = create_connection(DB_PATH)

    # Seed a small, illustrative operator/plant/service-category landscape.
    edf = insert_operator(conn, "EDF", "France", is_existing_customer=True,
                           relationship_notes="Long-standing framework customer")
    engie = insert_operator(conn, "ENGIE Electrabel", "Belgium", is_existing_customer=False)

    gravelines = insert_plant(conn, "Gravelines", "France", "PWR", 900, 1980, edf)
    doel = insert_plant(conn, "Doel", "Belgium", "PWR", 1000, 1975, engie)

    steam_gen_category = insert_service_category(conn, "Steam Generator Inspection", 500_000)
    overhaul_category = insert_service_category(conn, "Major Overhaul", 2_000_000)
    unplanned_category = insert_service_category(conn, "Unplanned", 300_000)

    category_lookup = {
        "Steam Generator Inspection": steam_gen_category,
        "Major Overhaul": overhaul_category,
        "Unplanned": unplanned_category,
    }
    plant_lookup = {"Gravelines": gravelines, "Doel": doel}

    extractor = MockExtractionClient()

    print("=== plant-outage-opportunity-database: AI-assisted extraction + scoring demo ===\n")

    for announcement in SAMPLE_ANNOUNCEMENTS:
        candidate = extractor.extract(announcement)
        print(f"Announcement: {announcement[:70]}...")
        print(f"  Extracted -> plant: {candidate.plant_name_guess}, reactor: {candidate.reactor_type_guess}, "
              f"outage: {candidate.outage_type_guess}, service: {candidate.service_category_guess}, "
              f"confidence: {candidate.confidence}")

        plant_id = plant_lookup.get(candidate.plant_name_guess)
        service_category_id = category_lookup.get(candidate.service_category_guess) or category_lookup.get(candidate.outage_type_guess)

        if plant_id is None or service_category_id is None:
            print("  -> Not enough extracted signal to create an opportunity automatically; would need manual review.\n")
            continue

        outage_id = insert_outage_event(conn, plant_id, candidate.outage_type_guess or "Unplanned",
                                         "2027-06-01", 30, scope_summary=announcement,
                                         source_reference="demo announcement")
        opportunity_id = create_scored_opportunity(
            conn, outage_id, service_category_id,
            estimated_value_eur=600_000, days_until_outage=250,
            identified_by="ai_assisted",
            notes=f"AI-extracted with confidence {candidate.confidence}",
        )
        print(f"  -> Created opportunity #{opportunity_id} (ai_assisted)\n")

    row_count = export_opportunities_csv_to_file(conn, CSV_PATH)
    print(f"Exported {row_count} opportunity row(s) to {CSV_PATH}")


if __name__ == "__main__":
    main()
