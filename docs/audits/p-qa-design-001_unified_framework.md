# Unified CWIP+TWIP QA Framework Design

**Date:** 2026-05-13
**Type:** Design memo (read-only, no execution)
**Status:** Pending owner approval

---

## 1. Current State

### 1.1 CWIP QA Artifacts (four separate systems)

**System A: cwip_qa_*.parquet tables (3 tables in data/delivery/)**

| Table | Rows | Schema | Purpose |
|-------|-----:|--------|---------|
| `cwip_qa_form5` | 275,932 | doc_id, api10, extraction_method, ocr_engine, ocr_confidence_mean, text_layer_present, page_count, char_count, extraction_success, extraction_quality, processed_at, pipeline_version, cache_path | Per-document extraction provenance for Form 5 |
| `cwip_qa_form5a` | 134,589 | Same as form5 + `verified` column | Per-document extraction provenance for Form 5A |
| `cwip_qa_sundry` | 277,685 | doc_id, extraction_method, ocr_confidence_mean, page_count, char_count, extraction_success, api_match, api_match_fuzzy, operator_match, operator_match_historical, spatial_match, verified, processed_at, error_message | Per-document extraction + linkage verification for Sundry |

**Assessment:** These are per-row extraction provenance tables, not check-based
QA tables. They track *how* each document was processed, not *whether* the
pipeline output meets acceptance criteria. Schema is inconsistent across the
three tables. None use the check_name/check_status/check_value pattern.

**System B: data/output/qa_reports/ markdown (9 files)**

| File | Covers |
|------|--------|
| `cwip_qa_bonds.md` | dim_bonds |
| `cwip_qa_bradenhead.md` | dim_bradenhead |
| `cwip_qa_drilling_permits.md` | dim_drilling_permits |
| `cwip_qa_injection.md` | dim_injection_volumes |
| `cwip_qa_inspections.md` | dim_inspections |
| `cwip_qa_mit.md` | dim_mit |
| `cwip_qa_noav.md` | dim_noav |
| `cwip_qa_plugging_docs.md` | dim_plugging_docs |
| `cwip_qa_spills.md` | dim_spill_reports |

**Assessment:** Per-pipeline diagnostic markdown reports. Human-readable but
not programmatically queryable. Cover 9 of 72 tables. Format varies per
report. Written at pipeline build time; not updated on re-runs.

**System C: docs/business/cwip_manual_qa_checklist.md**

Manual pre-launch verification checklist. Covers:
- Production numbers (5-10 wells against ECMC MonthlyProdRpt)
- Inspection records
- Operator history
- Well master attributes (status, location, type)
- Cross-table join verification

**Assessment:** Manual spot-check protocol for things automation can't fully
replace (visual verification against ECMC web UI, narrative coherence). Well
designed for its purpose. Not a substitute for automated programmatic QA.

**System D: No docs/qa_framework.md exists in CWIP**

### 1.2 TWIP QA Artifacts (two systems)

**System A: docs/qa_framework.md (65 lines)**

Formal three-level framework document:
- Level 1: Ingestion Validation (source_hash, row_count, schema, pk_unique,
  required_nonnull, record_type_distribution)
- Level 2: Referential Integrity (fk_match_rate, orphan_count,
  cardinality_sanity)
- Level 3: Analytical Sanity (production_spot_check, well_count_sanity,
  operator_count_sanity)

Defines companion table schema: ingestion_run_id, check_name, check_level,
check_status, check_value, check_threshold, checked_at, notes.

**Assessment:** Well designed. Correct architecture. But mostly aspirational —
companion tables are not populated for most tables.

**System B: twip_qa_production_monthly.parquet (11 rows)**

| Content | Rows |
|---------|-----:|
| PDQ verification spot checks (Level 3) | 10 |
| Overall verification summary | 1 |

Uses the framework schema correctly (ingestion_run_id, check_name,
check_level, check_status, check_value, check_threshold, checked_at, notes).

**Assessment:** Only QA companion table populated. Covers 1 of 15 tables.
But its schema is the right one.

### 1.3 Summary of Fragmentation

| Dimension | CWIP | TWIP |
|-----------|------|------|
| Framework document | Missing | Exists (docs/qa_framework.md) |
| Companion table schema | 3 tables, inconsistent schema, provenance-oriented | 1 table, consistent schema, check-oriented |
| Markdown reports | 9 pipeline reports (not queryable) | None |
| Manual checklist | Exists | None |
| Tables with any QA coverage | 12 of 72 (17%) | 1 of 15 (7%) |
| Programmatic check pattern | None | Defined but mostly unpopulated |

---

## 2. Real Issues Encountered (and What Would Have Caught Them)

### 2.1 Issue Classification

| # | Issue | Source | Severity | QA Level | Caught By | Before Ship? | Automated Check? |
|---|-------|--------|----------|----------|-----------|-------------|-----------------|
| 1 | Delivery table count mismatch (33 vs 72) | P363-C1 | CRITICAL | L1 | P363 audit | No | **Yes:** `delivery_table_count == manifest_count` |
| 2 | Future first_prod_date (2028-2029) | P363-C2 | CRITICAL | L1 | P363 audit | No | **Yes:** `max(date_column) <= today + 6 months` |
| 3 | 25 operator name → multiple operator_number | P363-M1 | MAJOR | L2 | P363 audit | No | **Yes:** `cardinality_check(operator_name → operator_number) == 1:1` |
| 4 | Consolidation over-grouping (151 in one family) | P363-M2 | MAJOR | L2 | P363 audit | No | **Yes:** `max_group_size < threshold` |
| 5 | 5 dtype inconsistencies across tables | P363-M3 | MAJOR | L1 | P363 audit | No | **Yes:** `dtype_consistency_across_tables(column_name)` |
| 6 | operator_number int64 vs str | P363-m1 | MINOR | L1 | P362 diag | No | **Yes:** `dtype_matches_data_dictionary` |
| 7 | 168 wells with no drilling permit | P363-m2 | MINOR | L2 | P363 audit | No | **Yes:** `fk_match_rate >= 99.9%` (actual 99.86%) |
| 8 | api10 vs api_norm join friction | P363-m3 | MINOR | L1 | P363 audit | No | **Yes:** `api_column_name == 'api10' on all tables` |
| 9 | Data dictionary claims stale (72/54.7M) | P363-m5 | MINOR | L1 | P363 audit | No | **Yes:** `manifest_row_count == actual_row_count` |
| 10 | 830 stale operators on well_master | P365 | MEDIUM | L2 | P365 audit | No | **Yes:** `cross_ref_consistency(well_master.operator, operator_history.is_current)` |
| 11 | is_horizontal False for 100% of wells | P365 | LOW | L1 | P365 audit | No | **Yes:** `boolean_column_not_uniform(is_horizontal)` |
| 12 | ~700K Wells sub-types without extraction | P367 | CRITICAL | L1 | P367 audit | No | **Yes:** `extraction_coverage_rate >= threshold per doc_type` |
| 13 | Corrected production report mismatch | P-TWIP-015-VERIFY | INFO | L3 | PDQ verification | Before | **Yes:** `spot_check_against_authoritative_source` |
| 14 | api10 duplicate characterization | P-TWIP-009/010 | INFO | L1 | Diagnostic prompt | Before | **Yes:** `pk_uniqueness` + `duplicate_distribution_analysis` |

### 2.2 Key Observation

**Every issue in the table above could have been caught by an automated check
before shipping.** 12 of 14 were caught only by ad-hoc audit prompts after the
fact. The two TWIP issues (#13, #14) were caught before shipping because TWIP
had the benefit of CWIP's lessons — but through manual prompts, not automated
framework checks.

A unified framework that runs these checks at ingestion time would have caught
all 14 issues at the point of origin.

---

## 3. Proposed Unified Framework

### 3.1 Canonical QA Artifact: Companion Table

Every table gets a QA companion:
- **Path:** `data/{layer}/{product}_qa_{table_slug}/{product}_qa_{table_slug}.parquet`
  - CWIP: `data/delivery/cwip_qa_{table_slug}.parquet`
  - TWIP: `data/raw/twip_qa_{table_slug}/twip_qa_{table_slug}.parquet`

**Schema (mandatory, uniform across both products):**

| Column | Type | Description |
|--------|------|-------------|
| `ingestion_run_id` | str | UUID or timestamp identifying the pipeline run |
| `check_name` | str | Machine-readable check identifier (e.g., `pk_unique`, `fk_match_rate_api10`) |
| `check_level` | int | 1, 2, or 3 |
| `check_status` | str | `pass`, `warn`, `fail`, or `error` |
| `check_value` | str | Observed value (e.g., "0 duplicates", "99.3% match") |
| `check_threshold` | str | Acceptance threshold (e.g., "0", ">99%") |
| `checked_at` | str | ISO 8601 UTC timestamp |
| `notes` | str | Context, sample values, or error details |

This is the schema TWIP's `twip_qa_production_monthly` already uses. It becomes
the universal standard.

### 3.2 Cross-Cutting Summary Table

Each product gets one summary table aggregating the latest check status per
(table, check_name) across all companion tables:

- `{product}_qa_summary.parquet`
- Built by scanning all companion tables, taking the most recent
  `checked_at` row per (table_slug, check_name)
- Provides a single-query view of product-wide quality status

### 3.3 Required Checks by Level

#### Level 1 — Ingestion Validation (every table, every run)

| Check Name | Description | Threshold | Motivated By |
|------------|-------------|-----------|-------------|
| `row_count_match` | Output row count matches source row count | Exact match | P363-C1, P363-m5 |
| `schema_match` | Output columns match data dictionary | All expected columns present | P363-M3 |
| `dtype_match` | Column dtypes match data dictionary | All match | P363-M3, P363-m1 |
| `pk_unique` | Primary key has no duplicates | 0 duplicates | P-TWIP-009/010 |
| `required_nonnull` | Required columns (PK, FK) have acceptable null rates | null rate < 1% for PKs, < 5% for FKs | P363-C2 |
| `date_range_sane` | Date columns within plausible range | No dates > today + 6 months | P363-C2 |
| `boolean_not_uniform` | Boolean flag columns are not 100% one value | At least 1 True and 1 False | P365 (is_horizontal) |
| `api_column_named_api10` | Well-referencing tables use `api10` column name | Column exists | P363-m3 |
| `identifier_columns_str` | All identifier columns (api10, operator_number, etc.) are str dtype | All str | P363-m1, P362 |

#### Level 2 — Referential Integrity (tables with FKs, run after related tables exist)

| Check Name | Description | Threshold | Motivated By |
|------------|-------------|-----------|-------------|
| `fk_match_rate` | FK values resolve to parent table PK | >= 99% (warn), >= 95% (fail) | P363-m2 |
| `orphan_distribution` | Distribution of orphan FK values by category | Documented, no single category > 50% of orphans | P363-m2 |
| `cardinality_bounds` | Expected 1:N relationships within bounds | Max N < product-specific threshold | P363-M2 |
| `cross_ref_consistency` | Snapshot fields match temporal source of truth | >= 99% match | P365 (830 stale operators) |
| `name_to_id_cardinality` | Name columns map 1:1 to ID columns | No name maps to 2+ IDs | P363-M1 |
| `dtype_consistency_across_tables` | Same column name has same dtype across all tables | All match | P363-M3 |

#### Level 3 — Analytical Sanity (tables with measurable content, run periodically)

| Check Name | Description | Criteria | Motivated By |
|------------|-------------|----------|-------------|
| `spot_check_authoritative` | N samples verified against authoritative source | 10 samples, exact match | P-TWIP-015-VERIFY |
| `count_sanity` | Total entity counts within expected range | Product-specific ranges | TWIP qa_framework.md |
| `extraction_coverage` | Extraction rate per document type | >= 90% (warn), >= 80% (fail) | P367 |
| `manifest_consistency` | Delivery manifest matches actual files | Exact match on table count and row counts | P363-C1, P363-m5 |

#### Product-Specific Checks

| Check | Product | Description | Motivated By |
|-------|---------|-------------|-------------|
| `corrected_report_handling` | TWIP | Flag lease-months where only original (not corrected) report exists | P-TWIP-015-VERIFY |
| `vision_coverage` | CWIP | Track % of documents with Vision pass vs Tesseract-only | P367 |

### 3.4 Failure Handling

| Status | Meaning | Pipeline Behavior |
|--------|---------|-------------------|
| `pass` | Check meets threshold | Continue |
| `warn` | Check outside ideal range but within tolerance | Log to companion table; pipeline continues; owner reviews periodically |
| `fail` | Check violates hard threshold | **Level 1 fail blocks pipeline commit** (raises PIPELINE_FAILED). Level 2/3 fail logs but does not block (cross-table checks may reflect upstream issues). |
| `error` | Check itself could not execute | Log with error details; pipeline continues; treated as warn for blocking purposes |

### 3.5 Retroactive QA

Every existing table gets a one-time historical QA run at framework adoption:
- All applicable Level 1 checks run against current output
- All applicable Level 2 checks run against current cross-table state
- Level 3 checks populated where authoritative verification has been done
  (e.g., TWIP production already has PDQ verification)
- Results stored in companion tables with `ingestion_run_id = 'retroactive-{date}'`

### 3.6 Ongoing QA Integration

Every future ingestion pipeline must:
1. Run all applicable Level 1 checks before committing output
2. Write results to companion table
3. Log check summary to pipeline log
4. Fail pipeline if any Level 1 check fails

Level 2 checks run as a cross-cutting job after ingestion batches complete.
Level 3 checks run periodically (monthly or on-demand).

### 3.7 CWIP Fragmentation Resolution

| Artifact | Disposition |
|----------|------------|
| `cwip_qa_form5.parquet` (275K rows) | **KEEP + RENAME** to `cwip_provenance_form5.parquet`. These are extraction provenance records (per-document metadata), not QA checks. They complement but don't replace the companion table pattern. |
| `cwip_qa_form5a.parquet` (134K rows) | **KEEP + RENAME** to `cwip_provenance_form5a.parquet`. Same rationale. |
| `cwip_qa_sundry.parquet` (277K rows) | **KEEP + RENAME** to `cwip_provenance_sundry.parquet`. Same rationale. |
| `data/output/qa_reports/*.md` (9 files) | **DEPRECATE.** Content migrates to companion table rows + pipeline logs. Archive to `data/output/qa_reports/archive/` with a README noting they're superseded by the unified framework. |
| `docs/business/cwip_manual_qa_checklist.md` | **KEEP.** Scope clarified: manual-only checks (visual verification against ECMC web UI, narrative review, chart sanity). All programmatic checks move to the unified framework. |

### 3.8 Shared Documentation

Both products get `docs/qa_framework.md` with identical structure:

```
# {Product} QA Framework

## Three-Level QA Pattern
  ### Level 1 — Ingestion Validation
  ### Level 2 — Referential Integrity
  ### Level 3 — Analytical Sanity

## Companion Table Schema

## Required Checks
  [Per-level check table with thresholds]

## Failure Handling

## Authoritative Sources for Level 3
  [Product-specific: ECMC for CWIP, RRC PDQ for TWIP]

## Integration with Pipeline Execution
  [Reference to operational_runbook.md]
```

Product-specific content is limited to:
- Authoritative source URLs (ECMC vs PDQ)
- Product-specific checks (corrected_report_handling, vision_coverage)
- Table-specific threshold values where they differ

---

## 4. What Changes

### For CWIP

| Change | Scope | Files Affected |
|--------|-------|---------------|
| Create `docs/qa_framework.md` | New file | 1 |
| Rename 3 `cwip_qa_*` → `cwip_provenance_*` | File rename + data dictionary update | 3 parquet + docs |
| Create new `cwip_qa_*` companion tables (check-based) | 72 tables x Level 1 checks = ~72 new parquets | 72 |
| Deprecate `data/output/qa_reports/*.md` | Archive 9 files | 9 |
| Scope-clarify `cwip_manual_qa_checklist.md` | Add header noting programmatic checks moved | 1 |
| Run retroactive QA on all 72 delivery tables | One-time batch | 72 companion tables populated |
| Update `CLAUDE.md` with QA framework reference | Add line | 1 |

### For TWIP

| Change | Scope | Files Affected |
|--------|-------|---------------|
| Replace `docs/qa_framework.md` with unified version | File rewrite | 1 |
| Populate companion tables for 15 existing tables | Retroactive QA run | 15 companion tables populated |
| Production monthly companion table already exists | No change needed | 0 |
| Update `CLAUDE.md` with QA framework reference | Add line | 1 |
| Integrate Level 1 checks into ingestion pipeline template | Code pattern addition | Template |

---

## 5. Implementation Sequence

| Step | Prompt | Repo | What It Does |
|------|--------|------|-------------|
| 1 | **P-QA-002** | CWIP | Create `docs/qa_framework.md`. Rename provenance tables. Deprecate qa_reports/ markdown. Scope-clarify manual checklist. Write `cwip_qa_check_runner.py` utility. Run retroactive Level 1 QA on all 72 delivery tables. |
| 2 | **P-QA-003** | TWIP | Replace `docs/qa_framework.md` with unified version. Write `twip_qa_check_runner.py` utility. Run retroactive Level 1+2 QA on all 15 existing tables. |
| 3 | **P-QA-004** | Both | Run Level 2 cross-table checks for both products. Build `{product}_qa_summary` cross-cutting tables. |
| 4 | Future ingestion | Both | All new ingestion prompts include Level 1 companion table generation as a pipeline requirement (already in TWIP operational runbook; add to CWIP). |

**Owner approves this design before any implementation prompts run.**
