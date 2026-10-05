# plant-outage-opportunity-database

A tested SQL database (SQLite) for the preliminary identification and
evaluation of business opportunities in the nuclear-plant outage revision
service domain. It combines an extensible schema, an explainable priority
scoring model, AI-assisted extraction of opportunities from unstructured text,
and automated CSV exports.

## What it does

- **`src/schema.py`** — a SQLite schema: `operators`, `plants`,
  `outage_events`, `service_categories`, `opportunities`, with foreign
  keys enforced, indexes on the columns that matter for the queries
  this database exists to answer, and `CREATE TABLE IF NOT EXISTS`
  throughout so the schema can be safely re-applied. It is designed for
  extension: adding a new table (e.g. competitor intelligence, contact
  records) or a new column to an existing one doesn't require
  restructuring what's there.
- **`src/scoring.py`** — a market-oriented, fully explainable scoring
  function for prioritizing plant types and customers by likelihood of
  success: existing-customer relationship, contract value relative to the
  service category's typical value (capped so a single outlier can't
  dominate), operator fleet size (more reactors → more repeat-business
  potential), and lead-time fit (too soon or too far out both score lower
  than a realistic preparation window). `compute_priority_breakdown()`
  returns the named, per-factor contributions, not just a final number, so
  a user can see exactly why an opportunity scored the way it did.
- **`src/ai_extraction.py`** — the AI-assisted extraction layer. It turns
  unstructured text (news snippets, outage announcements) into structured
  candidate opportunities. `MockExtractionClient` is a deterministic,
  rule-based extractor that parses text for reactor-type mentions,
  outage/service keywords, and plant names; different inputs produce
  different, input-appropriate outputs, and this is directly tested.
  `RealAnthropicExtractionClient` is the live-LLM counterpart behind the same
  interface; it raises immediately if instantiated without an API key rather
  than silently falling back to mock behavior.
- **`src/repository.py`** — the parameterized-SQL data-access layer
  (`sqlite3` directly, no string-concatenated SQL, so no SQL-injection
  risk) tying scoring to persistence: `create_scored_opportunity()` looks up
  the context (operator relationship, fleet size, category typical value)
  and inserts a fully scored opportunity row in one call.
- **`src/export.py`** — automated extracts: a tested CSV export of the
  opportunities view, ordered by priority score, usable as a scheduled
  report.
- **`run_demo.py`** — an end-to-end run: seeds a small illustrative
  landscape, feeds three outage-announcement-style text snippets through the
  AI-assisted extractor, scores and inserts the resulting opportunities, and
  produces a CSV export. One snippet is flagged for manual review rather than
  guessed at, when the extractor doesn't have enough signal.

## Data

All plant, operator, and outage data is illustrative and synthetic. The
sample data (`run_demo.py`) uses publicly known plant and operator names
(Gravelines, Doel, EDF, ENGIE) as realistic labels; the outage dates, scope,
and values are made up. The pipeline is built so real sources can replace
them.

## Tests

52 tests across schema, scoring, AI extraction, repository, and export, all
passing.

A bug caught along the way: the plant-name extraction regex
(`src/ai_extraction.py`) originally matched "Gravelines Nuclear" instead of
"Gravelines" for the input "Gravelines Nuclear Power Plant", because the
optional second-word capture group consumed the word "Nuclear" before the
literal "Nuclear" keyword match. `test_extracts_plant_name_before_nuclear_keyword`
caught it, and a negative lookahead excluding "Nuclear"/"Power"/"Plant" from
the captured name fixed it.

## Project structure

```
src/        schema.py, scoring.py, ai_extraction.py, repository.py, export.py
tests/      test_schema.py, test_scoring.py, test_ai_extraction.py,
            test_repository.py, test_export.py
run_demo.py
requirements.txt, pytest.ini
```

## Running it

```bash
pip install -r requirements.txt
python -m pytest -v      # run the full test suite
python run_demo.py       # run the AI-extraction + scoring + export demo
```

## Notes

The demo runs with the rule-based `MockExtractionClient`, so it needs no API
key or network access. `RealAnthropicExtractionClient` contains the live API
call; its response parsing is the piece to complete when running against a
live model.

## Possible extensions

- Add tables for competitor intelligence and contact records.
- Finish response parsing in `RealAnthropicExtractionClient` and run it
  against a live model.
- Schedule the CSV export as a recurring report.
