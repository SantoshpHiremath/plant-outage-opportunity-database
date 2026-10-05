"""
Automated exports: scheduled-style extracts are a design requirement for
this database, not just manual ad-hoc queries. This module provides a
tested CSV export of the opportunities view -- the kind of scheduled
report a business-development team would pull from this database.
"""
import csv
import io
import sqlite3

OPPORTUNITY_EXPORT_QUERY = """
SELECT
    o.opportunity_id,
    op.operator_name,
    p.plant_name,
    p.country,
    p.reactor_type,
    oe.outage_type,
    oe.planned_start_date,
    sc.category_name AS service_category,
    o.estimated_value_eur,
    o.priority_score,
    o.priority_tier,
    o.status,
    o.identified_by
FROM opportunities o
JOIN outage_events oe ON o.outage_id = oe.outage_id
JOIN plants p ON oe.plant_id = p.plant_id
JOIN operators op ON p.operator_id = op.operator_id
JOIN service_categories sc ON o.service_category_id = sc.service_category_id
ORDER BY o.priority_score DESC
"""


def export_opportunities_csv(conn: sqlite3.Connection) -> str:
    """Runs the opportunity export query and returns the result as a
    CSV-formatted string. Kept as a pure string-returning function
    (rather than writing directly to a file) so it's easy to test
    without touching the filesystem, and so a caller can choose to
    write it to disk, attach it to an email, or stream it elsewhere."""
    cursor = conn.execute(OPPORTUNITY_EXPORT_QUERY)
    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(column_names)
    writer.writerows(rows)
    return buffer.getvalue()


def export_opportunities_csv_to_file(conn: sqlite3.Connection, file_path: str) -> int:
    """Writes the CSV export to file_path and returns the number of
    data rows written (excluding the header)."""
    csv_content = export_opportunities_csv(conn)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        f.write(csv_content)
    return csv_content.count("\n") - 1  # header line doesn't count as a data row
