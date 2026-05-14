# TWIP QA Framework

*Unified framework per P-QA-DESIGN-001 (commit 7aed304). Mirrors CWIP qa_framework.md.*

---

## Three-Level QA Pattern

### Level 1 — Ingestion Validation (every table, every run)

Every ingestion pipeline MUST produce these checks:

| Check | Description | Acceptance Criteria |
|---|---|---|
| row_count | Output row count matches expected | PASS = within 1% or exact match |
| schema_match | Output columns match data dictionary | PASS = all expected columns present |
| dtype_match | Column dtypes match data dictionary | PASS = all match |
| pk_unique | Primary key has no duplicates | PASS = 0 duplicates |
| required_nonnull | Required columns (PK, FK) have acceptable null rates | PASS = null rate < threshold |
| date_range_sane | Date columns within plausible range | PASS = no dates > today + 6 months |
| boolean_not_uniform | Boolean columns not 100% one value | WARN if uniform |
| identifier_columns_str | All ID columns (api10, operator_number, district) are str dtype | PASS = all str |

### Level 2 — Referential Integrity (cross-table)

Run after all related tables are ingested:

| Check | Description | Acceptance Criteria |
|---|---|---|
| fk_match_rate | FK column values resolve to parent table PK | PASS = >=99%, WARN = 95-99%, FAIL = <95% |
| orphan_count | Rows whose FK does not resolve | WARN if >5%, FAIL if >20% |
| cardinality_bounds | Expected 1:N relationships within bounds | PASS = within expected ranges |
| cross_ref_consistency | Snapshot fields match temporal source of truth | PASS = >=99% match |
| dtype_consistency | Same column name has same dtype across all tables | PASS = all match |

### Level 3 — Analytical Sanity (spot checks)

Per-source verification against RRC's authoritative query systems:

| Check | Description | Acceptance Criteria |
|---|---|---|
| spot_check_authoritative | N samples verified against authoritative source | PASS = 10 samples exact match |
| count_sanity | Total entity counts within expected range | PASS = within range |
| manifest_consistency | Delivery manifest matches actual files | PASS = exact match |

---

## Companion Table Schema

Every `twip_qa_<slug>.parquet` uses this consistent schema:

| Column | Type | Description |
|---|---|---|
| ingestion_run_id | str | UUID or timestamp identifying the pipeline run |
| check_name | str | Machine-readable check identifier |
| check_level | int | 1, 2, or 3 |
| check_status | str | "pass", "fail", "warn", or "error" |
| check_value | str | Observed value |
| check_threshold | str | Acceptance threshold |
| checked_at | str | ISO 8601 UTC timestamp |
| notes | str | Additional context |

Results stored in: `data/raw/twip_qa_<table_slug>/twip_qa_<table_slug>.parquet`

---

## Failure Handling

| Status | Meaning | Pipeline Behavior |
|---|---|---|
| pass | Check meets threshold | Continue |
| warn | Outside ideal range but within tolerance | Log; pipeline continues; owner reviews periodically |
| fail | Violates hard threshold | Level 1 fail blocks pipeline commit (PIPELINE_FAILED). Level 2/3 fail logs but does not block. |
| error | Check itself could not execute | Log with details; treated as warn for blocking purposes |

---

## Authoritative Sources for Level 3

TWIP's authoritative sources for spot-check verification:
- Production: RRC PDQ (https://webapps.rrc.texas.gov/PDQ/)
  - Verified in P-TWIP-015-VERIFY-AUTO: 10/10 exact match
- Permits: RRC online permit query
- Well registry: RRC Statewide API Data

---

## Integration with Pipeline Execution

Per docs/operational_runbook.md: every ingestion pipeline runs Level 1 checks
before declaring PIPELINE_COMPLETE. Level 1 fail triggers PIPELINE_FAILED.
Level 2 checks run as cross-cutting validation after related tables are
ingested. Level 3 checks run periodically or on-demand.

Run QA via: `python scripts/qa/run_qa_for_table.py --table-slug <slug>`
Run all:    `python scripts/qa/run_qa_for_table.py --all`
