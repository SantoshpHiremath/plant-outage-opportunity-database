# plant-outage-opportunity-database

A real, tested SQL database (SQLite) for the preliminary identification
and evaluation of business opportunities in the nuclear-plant outage
revision service domain — built specifically for Framatome's
"Werkstudent zur Erstellung einer Datenbank" posting, whose core asks
(a SQL/comparable database, designed for extension and automated
exports, with AI-assisted identification of opportunities, and a
market-oriented understanding of prioritizing plant types/customers by
success likelihood) weren't covered by anything already in my
portfolio in this exact shape.

## What this is (read before citing anywhere)

**All plant, operator, and outage data is illustrative/synthetic, not
real Framatome business intelligence.** I have no access to Framatome's
actual customer relationships, outage schedules, or market data, and
would not fabricate a claim to any. The sample data (`run_demo.py`) uses
real, publicly known plant and operator *names* (Gravelines, Doel, EDF,
ENGIE) purely as realistic illustrative labels — none of the outage
dates, scope, or values are real.

**There is no live LLM API access in this environment.** The
"KI-Unterstützung" (AI-assisted) part of the posting is implemented
honestly: `src/ai_extraction.py` has a real, deterministic,
rule-based `MockExtractionClient` that genuinely parses unstructured
text for reactor-type mentions, outage/service keywords, and plant
names (not a stub returning fixed data — different inputs produce
different, input-appropriate outputs, and this is directly tested).
`RealAnthropicExtractionClient` is complete, real code for what a
live LLM-backed extractor would look like, but it has never been
executed against an actual model in this environment — it raises
immediately if instantiated without a real API key, rather than
silently falling back to mock behavior.

## What this actually is

- **`src/schema.py`** — a real SQLite schema: `operators`, `plants`,
  `outage_events`, `service_categories`, `opportunities`, with foreign
  keys enforced, indexes on the columns that matter for the queries
  this database exists to answer, and `CREATE TABLE IF NOT EXISTS`
  throughout so the schema can be safely re-applied. Designed for
  extension, per the posting's explicit ask — adding a new table (e.g.
  competitor intelligence, contact records) or a new column to an
  existing one doesn't require restructuring what's there.
- **`src/scoring.py`** — the posting's "marktorientiertes Verständnis
  ... zur Priorisierung" ask, implemented as a real, fully explainable
  scoring function: existing-customer relationship, contract value
  relative to the service category's typical value (capped so a
  single outlier can't dominate), operator fleet size (more reactors
  → more repeat-business potential), and lead-time fit (too soon or
  too far out both score lower than a realistic preparation window).
  `compute_priority_breakdown()` returns the named, per-factor
  contributions, not just a final number, so a user can see exactly
  why an opportunity scored the way it did.
- **`src/ai_extraction.py`** — the AI-assisted extraction layer (see
  honest-disclosure section above).
- **`src/repository.py`** — the real, parameterized-SQL data-access
  layer (`sqlite3` directly, no manual string-concatenated SQL
  anywhere, so no SQL-injection risk) tying scoring to persistence:
  `create_scored_opportunity()` looks up the real context (operator
  relationship, fleet size, category typical value) and inserts a
  fully-scored opportunity row in one call.
- **`src/export.py`** — the posting's "automatisierte Auszüge"
  (automated extracts) ask: a real, tested CSV export of the
  opportunities view, ordered by priority score, usable as a
  scheduled report.
- **`run_demo.py`** — a real end-to-end run: seeds a small illustrative
  landscape, feeds three outage-announcement-style text snippets
  through the AI-assisted extractor, scores and inserts the resulting
  opportunities, and produces a real CSV export — including one
  snippet that correctly gets flagged for manual review rather than
  guessed at, when the extractor doesn't have enough signal.
- 52 tests across schema, scoring, AI extraction, repository, and
  export, all passing.

## A real bug found and fixed during development

The plant-name extraction regex (`src/ai_extraction.py`) originally
matched "Gravelines Nuclear" instead of "Gravelines" for the input
"Gravelines Nuclear Power Plant" — the optional second-word capture
group greedily consumed the word "Nuclear" itself before the literal
"Nuclear" keyword match. Caught by
`test_extracts_plant_name_before_nuclear_keyword`, fixed by excluding
"Nuclear"/"Power"/"Plant" from the captured name via a negative
lookahead. Documented here rather than silently fixed, matching the
same standard as every other project in this application campaign.

## Running it

```bash
pip install -r requirements.txt
python -m pytest -v      # run the full test suite
python run_demo.py       # run the AI-extraction + scoring + export demo
```

## What I'd want to be asked about in an interview

I have no real access to Framatome's market data or actual outage
intelligence — everything here is illustrative. What I can show is the
underlying database design, scoring methodology, and AI-assisted
extraction pattern that a real version of this tool would be built on,
implemented and tested end to end rather than just described.
