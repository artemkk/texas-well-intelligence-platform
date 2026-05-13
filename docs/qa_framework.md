# TWIP QA Framework

*Last updated: 2026-05-13*

---

## Three-Level QA Pattern

### Level 1 — Ingestion Validation (per pipeline run)

Every ingestion pipeline MUST produce these checks:

| Check | Description | Acceptance Criteria |
|---|---|---|
| source_hash_match | SHA-256 of source matches source_meta.json | PASS = exact match |
| raw_row_count | Raw table row count == source row count | PASS = equal |
| schema_match | Output columns match expected schema | PASS = all expected columns present |
| pk_unique | Primary key has no duplicates (master/dim tables) | PASS = 0 duplicates |
| required_nonnull | Required columns (PK, FK) have acceptable null rates | PASS = null rate < threshold |
| record_type_distribution | Counts per record type match expected patterns | PASS = no missing types |

Results stored in: `data/raw/twip_qa_<table_slug>/twip_qa_<table_slug>.parquet`

### Level 2 — Referential Integrity (cross-table)

Run after all related tables are ingested:

| Check | Description | Acceptance Criteria |
|---|---|---|
| fk_match_rate | FK column values resolve to parent table PK | PASS = >95% match rate |
| orphan_count | Rows whose FK doesn't resolve | WARN if >5%, FAIL if >20% |
| cardinality_sanity | Expected 1:N or N:M relationships verified | PASS = within expected ranges |

### Level 3 — Analytical Sanity (spot checks)

Per-source verification against RRC's authoritative query systems:

| Check | Description | Acceptance Criteria |
|---|---|---|
| production_spot_check | 5-10 lease-months verified against PDQ | PASS = values match within 1% |
| well_count_sanity | Total wells within expected range (1M-1.5M) | PASS = within range |
| operator_count_sanity | Total operators within expected range (30K-80K) | PASS = within range |

---

## QA Companion Table Schema

Every `twip_qa_<slug>.parquet` uses this consistent schema:

| Column | Type | Description |
|---|---|---|
| ingestion_run_id | str | UUID or timestamp identifying the pipeline run |
| check_name | str | Name of the QA check (e.g., "pk_unique") |
| check_level | int | 1, 2, or 3 |
| check_status | str | "pass", "fail", or "warn" |
| check_value | str | Observed value (e.g., "0 duplicates", "99.3% match") |
| check_threshold | str | Acceptance threshold (e.g., "0", ">95%") |
| checked_at | str | ISO 8601 UTC timestamp |
| notes | str | Any additional context |

---

## Standing Rule

Per docs/operational_runbook.md: every ingestion prompt MUST produce Level 1 QA results as part of its pipeline output. Level 2 and Level 3 checks are run separately as cross-cutting validation.
