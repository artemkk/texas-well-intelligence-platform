# CWIP vs TWIP Documentation Format Comparison

**Date:** 2026-05-13
**Type:** Read-only diagnostic
**Purpose:** Surface every divergence in documentation format, naming,
structure, and location between CWIP and TWIP so reconciliation can
be sequenced in subsequent prompts.

---

## 1. CWIP Documentation Inventory

### docs/ (root-level documentation)

| File | Lines | Description |
|------|------:|-------------|
| `docs/cwip_data_inventory.md` | 245 | Master data inventory — every source, table, pipeline, and how they connect |
| `docs/operational_runbook.md` | 927 | Pipeline operations, monitoring, crash detection, monthly orchestration, per-pipeline rules |
| `docs/pipeline_scoping_notes.md` | 652 | Per-pipeline scoping for all Phase 2 document classes |
| `docs/cwip_overview_nontechnical.md` | 259 | Buyer-facing plain-English guide to CWIP structure and content |
| `docs/ecmc_data_gaps.md` | 212 | Known regulatory record gaps, misfiled documents, filing anomalies |
| `docs/scheduled_tasks.md` | 162 | Windows Task Scheduler setup for monthly orchestration |
| `docs/laserfiche_document_inventory.md` | 161 | Laserfiche archive breakdown by document class and processing status |
| `docs/dev_log_format.md` | 82 | Dev log formatting conventions |
| `docs/dev_log_s01_s26.md` | — | Historical dev log (sessions 1-26) |
| `docs/dev_log_s27_s52.md` | — | Historical dev log (sessions 27-52) |
| `docs/terminology.md` | 53 | Core terminology and entity definitions |
| `docs/project_truths.md` | 44 | Foundational product axioms and guardrails |
| `docs/api_renumbering_investigation.md` | — | API number edge case investigation |
| `docs/discovery_monthly_wells_job.md` | — | Monthly Wells.shp update discovery |
| `docs/phase2_tracking.md` | — | Phase 2 pipeline completion tracking |

### docs/audits/

| File | Lines | Description |
|------|------:|-------------|
| `p367_ocr_coverage_audit.md` | 511 | OCR extraction coverage gaps across Wells sub-types |
| `p363_cwip_audit_report.md` | 198 | Comprehensive CWIP audit (14 findings) |
| `p365_derived_attributes_audit.md` | 85 | Stale operators and is_horizontal audit |
| `p364_completion_report.md` | 59 | Audit fix execution report |
| `p368_deferred_sub_types.md` | 53 | Deferred Wells sub-type extraction list |

### docs/business/

| File | Lines | Description |
|------|------:|-------------|
| `elareon_strategy.md` | 770 | Master business strategy document |
| `phase3_scoping.md` | 516 | Phase 3 external source scoping |
| `cwip_delivery_architecture.md` | 456 | S3 delivery, watermarking, Lemon Squeezy integration |
| `phase2b_scoping.md` | 336 | Phase 2b (vision model) scoping |
| `cwip_market_positioning.md` | 290 | Market positioning and competitive analysis |
| `cwip_manual_qa_checklist.md` | 220 | Pre-launch manual QA verification steps |
| `cwip_licensing_architecture.md` | 149 | Licensing model and subscription tiers |
| `cwip_beta_launch.md` | 135 | Beta launch plan |

### docs/content/

| File | Lines | Description |
|------|------:|-------------|
| `content_pipeline.md` | 319 | Substack content strategy and editorial pipeline |

### docs/onboarding/

| File | Lines | Description |
|------|------:|-------------|
| `video_script.md` | 282 | Onboarding video script |
| `video_roadmap.md` | 227 | Onboarding video series roadmap |

### docs/articles/

| Directory | Description |
|-----------|-------------|
| `article-01-dj-basin-decline-by-vintage/` | DJ Basin productivity analysis (published) |
| `article-02-permit-to-first-production/` | Permit-to-production timeline analysis |
| `article-03-bradenhead-leading-indicator/` | Bradenhead pressure as leading indicator |
| `article-04-dj-basin-operator-rankings/` | Multi-metric operator rankings |
| `acreage-evaluation-civitas-weld-county/` | Civitas acreage evaluation case study |

### docs/papers/

| File | Description |
|------|-------------|
| `dj_basin_productivity_drivers/draft_v1.md` | Academic paper draft (halted) |

### Buyer-facing PDFs (generated, in data/output/_pdf_test/)

| File | Size | Description |
|------|-----:|-------------|
| `cwip_data_dictionary.pdf` | 1.0 MB | 22-page branded data dictionary with per-column documentation |

**Note:** The `data/delivery/docs/` directory was lost during P342 git filter-repo cleanup.
It previously contained: `cwip_data_dictionary.pdf`, `cwip_data_inventory.pdf`,
`cwip_data_inventory.md`, `CWIP_Getting_Started_Guide.pdf`, `cwip_methodology.md/pdf`,
`cwip_quickstart.md/pdf`, `cwip_coverage_notes.md/pdf`, `CHANGELOG.md`. These are
recoverable from backups but currently absent from the repo.

### Other documentation locations

| Location | Count | Description |
|----------|------:|-------------|
| `data/diagnostics/*.md` | 90 | Per-prompt diagnostic reports and investigations |
| `docs/business/phase*.md` | 2 | Phase scoping docs under business/ |

### CWIP has NO standalone:
- `data_dictionary.md` (column-level docs are in the PDF only)
- `source_inventory.md` (sources documented inside `cwip_data_inventory.md`)
- `qa_framework.md` (QA approach is in `cwip_manual_qa_checklist.md` and per-pipeline)
- `delivery_bundle_manifest.md` (delivery info is in `cwip_delivery_architecture.md`)
- `cross_state_comparison.md` (exists only in TWIP)

---

## 2. TWIP Documentation Inventory

### docs/ (root-level documentation)

| File | Lines | Description |
|------|------:|-------------|
| `docs/data_dictionary.md` | 247 | Column-by-column schema for all output tables |
| `docs/operational_runbook.md` | 196 | Standing rules: zero-skip, pipeline execution, Playwright, docs-per-ingestion |
| `docs/cross_state_comparison.md` | 201 | CWIP vs TWIP architectural differences |
| `docs/source_inventory.md` | 112 | Per-source documentation with URLs, formats, fetchers, status |
| `docs/qa_framework.md` | 65 | Three-level QA pattern with companion table schema |
| `docs/delivery_bundle_manifest.md` | 56 | Buyer-facing product description, coverage stats, pricing |

### docs/audits/

| File | Lines | Description |
|------|------:|-------------|
| `p-twip-015-verify_pdq_verification.md` | 125 | Automated PDQ production parser verification |

### docs/ placeholder directories

| Directory | Contents |
|-----------|----------|
| `docs/articles/` | `.gitkeep` only |
| `docs/business/` | `.gitkeep` only |
| `docs/onboarding/` | `.gitkeep` only |
| `docs/papers/` | `.gitkeep` only |

### Scoping documents (data/diagnostics/)

| File | Lines | Description |
|------|------:|-------------|
| `p-twip-001_phase_scoping.md` | 241 | Three-phase scoping plan |
| `p-twip-001_rrc_inventory.md` | 189 | Phase 1 RRC source inventory |
| `p-twip-001_tx_external_inventory.md` | 174 | Phase 3 Texas-specific external sources |
| `p-twip-001_federal_reuse.md` | 84 | Federal sources reusable from CWIP Phase 3 |

### Root-level

| File | Lines | Description |
|------|------:|-------------|
| `README.md` | 5 | Minimal placeholder |

### TWIP has NO:
- Buyer-facing PDFs (data dictionary, getting started guide, etc.)
- `cwip_overview_nontechnical.md` equivalent
- `ecmc_data_gaps.md` / data gaps document
- Content pipeline / article infrastructure (placeholder only)
- Business strategy documents (placeholder only)
- Onboarding materials (placeholder only)
- Dev logs
- Terminology / project truths documents
- Scheduled tasks documentation
- Pipeline scoping notes (per-pipeline detail)
- Manual QA checklist

---

## 3. Structural Divergences

### 3.1 Document-by-Document Comparison

| Aspect | CWIP | TWIP | Divergence |
|--------|------|------|------------|
| **Data dictionary** | PDF only (`cwip_data_dictionary.pdf`, 22 pages). No standalone `.md`. | `docs/data_dictionary.md` (247 lines). No PDF. | **YES — format and column schema** |
| **Data dictionary columns** | Column \| Type \| Nulls \| Description \| Example | Column \| Type \| Source/Description | **YES — CWIP has Nulls + Example; TWIP has Source** |
| **Data dictionary per-table header** | Table name, Description paragraph, Row count | Table name, brief description, Primary key noted | **YES — CWIP has row count; TWIP has PK documentation** |
| **Source/data inventory** | `docs/cwip_data_inventory.md` — combined source+table+pipeline inventory (245 lines) | `docs/source_inventory.md` — source-only (112 lines). Tables in separate `data_dictionary.md`. | **YES — CWIP combines; TWIP separates** |
| **Source inventory per-entry** | Table: Rows \| Source \| Join Key \| QA Report \| Last Updated \| Description | Bulleted list: URL, Format, Encoding, Refresh, Layout doc, Fetcher, Ingestion, Output tables, Status, Last ingestion, Notes | **YES — TWIP has richer per-source metadata** |
| **QA framework** | `docs/business/cwip_manual_qa_checklist.md` (220 lines). Manual spot-check approach. No formal level system. | `docs/qa_framework.md` (65 lines). Formal 3-level system (Ingestion, Referential, Analytical). Companion table schema defined. | **YES — TWIP has formal framework; CWIP has manual checklist** |
| **Operational runbook** | `docs/operational_runbook.md` (927 lines). Mature: monthly orchestration, watchdog, crash recovery, per-pipeline rules. | `docs/operational_runbook.md` (196 lines). Early: standing rules for pipeline execution, Playwright, zero-skip. | **YES — same path, different maturity** |
| **Delivery manifest** | `docs/business/cwip_delivery_architecture.md` (456 lines). Technical: S3, watermarking, webhooks. | `docs/delivery_bundle_manifest.md` (56 lines). Buyer-facing: product description, coverage, pricing. | **YES — different audiences, different locations** |
| **Cross-state comparison** | Does not exist | `docs/cross_state_comparison.md` (201 lines) | **YES — TWIP only** |
| **Overview / quickstart** | `docs/cwip_overview_nontechnical.md` (259 lines). Buyer-facing, table-by-table walkthrough. | Does not exist | **YES — CWIP only** |
| **Data gaps** | `docs/ecmc_data_gaps.md` (212 lines). Misfiled docs, coverage gaps, filing anomalies. | Does not exist | **YES — CWIP only** |

### 3.2 Structural Pattern Divergences

| Pattern | CWIP | TWIP | Assessment |
|---------|------|------|------------|
| **Scoping docs location** | `docs/business/phase*.md` | `data/diagnostics/p-twip-001_*.md` | **Divergent.** CWIP puts scoping under business/; TWIP under data/diagnostics/. |
| **Audit naming** | `p363_cwip_audit_report.md` (prompt number, no prefix) | `p-twip-015-verify_pdq_verification.md` (product prefix + prompt number + description) | **Divergent.** TWIP naming is more descriptive. |
| **Runbook scope** | Operational procedures (how to run things) | Standing rules (what rules to follow) | **Divergent intent.** CWIP runbook = ops manual. TWIP runbook = policy document. |
| **Doc organization** | Flat under `docs/` with `docs/business/` for strategy, `docs/content/` for editorial | Flat under `docs/` with empty placeholder subdirs | **Consistent pattern, different maturity** |

---

## 4. Naming Convention Divergences

### 4.1 Table Name Prefixes

| Prefix | CWIP Tables | TWIP Tables | Notes |
|--------|------------|------------|-------|
| `{product}_well_master` | `cwip_well_master` | `twip_well_master` | Consistent |
| `{product}_production_monthly` | `cwip_production_monthly` | — | CWIP omits `fact_` prefix |
| `{product}_fact_production_monthly` | — | `twip_fact_production_monthly` | TWIP uses `fact_` prefix |
| `{product}_dim_*` | 16 tables | 5 tables | Consistent prefix |
| `{product}_fact_*` | 22 tables | 5 tables | Consistent prefix |
| `{product}_ref_*` | 17 tables | 0 tables | **CWIP only** — Phase 3 external sources |
| `{product}_qa_*` | 3 tables | 1 table | Consistent prefix |

**Key divergence:** CWIP's `cwip_production_monthly` lacks the `fact_` prefix that
its star-schema position warrants. TWIP correctly uses `twip_fact_production_monthly`.
CWIP should backport the `fact_` prefix for consistency.

### 4.2 Table Name Divergences for Equivalent Concepts

| Concept | CWIP | TWIP | Divergence |
|---------|------|------|------------|
| Well master | `cwip_well_master` | `twip_well_master` | None |
| Operator registry | (embedded in well_master) | `twip_dim_operator_registry` | **YES** — TWIP has standalone table |
| Operator history | `cwip_dim_operator_history` | `twip_dim_operator_history` | None |
| Operator consolidation | `cwip_dim_operator_consolidation` | (unprefixed: `operator_consolidation`) | **YES** — TWIP missing prefix |
| Drilling permits | `cwip_dim_drilling_permits` | `twip_dim_drilling_permits` | None |
| Inspections | `cwip_dim_inspections` | `twip_fact_inspections` | **YES** — dim vs fact classification |
| Production | `cwip_production_monthly` | `twip_fact_production_monthly` | **YES** — missing fact_ prefix in CWIP |
| Raw preservation | (not used) | `*_raw` suffix tables | **YES** — TWIP pattern, no CWIP equivalent |
| Well completions | (not applicable) | `twip_fact_well_completions` | TWIP-specific (Texas dual-key system) |
| Well-lease crosswalk | (not applicable) | `twip_dim_well_lease_crosswalk` | TWIP-specific (lease-level production) |

### 4.3 Column Name Divergences

| Concept | CWIP well_master | TWIP well_master | Divergence |
|---------|-----------------|-----------------|------------|
| API 10-digit | `api10` (str) | `api10` (str) | None |
| Total depth | `total_depth_ft` (float64) | `total_dept` (str) | **YES** — naming and type |
| Section | `section` (str) | `section` (str) | None |
| Operator name | `operator_name` (str) | (not in master) | Different architecture |
| Operator number | `operator_number` (str) | (not in master) | Different architecture |
| Ingestion timestamp | `ingest_batch_id` (str) | `scraped_at` (str) | **YES** — different naming |
| Source tracking | `source_system` + `source_well_id` + `source_row_hash` | `source_file` | **YES** — CWIP has richer provenance |
| State code | `api_state_code` (str) | (derived in api10 prefix "42") | **YES** — CWIP explicit; TWIP implicit |

### 4.4 Column Count Comparison (well_master)

| Dimension | CWIP | TWIP |
|-----------|------|------|
| Total columns | 49 | 11 |
| Identity columns | 11 (well_id through api10) | 2 (api10, apinum) |
| Location columns | 10 (lat/lon/UTM/elevation/PLSS) | 0 |
| Operator columns | 5 | 0 (operator is in completions) |
| Classification columns | 6 (type, status, direction) | 0 |
| Date columns | 6 (spud, completion, first/last prod, plug, status_effective) | 0 |
| Boolean flags | 7 (is_horizontal, is_injection, etc.) | 0 |
| Provenance columns | 4 (source_system, hash, batch, api_state) | 2 (scraped_at, source_file) |
| Texas-specific columns | 0 | 7 (apinum, abstract, block, survey, etc.) |

**Assessment:** CWIP well_master is heavily enriched with derived attributes,
location data, and boolean flags. TWIP well_master is a raw preservation table
with only intrinsic well properties from the source. This is an intentional
architectural difference (TWIP's column classification rule: WELL_PROPERTY vs
EVENT_PROPERTY), not drift. TWIP will need enrichment passes to reach CWIP parity.

### 4.5 Abbreviation Conventions

| Concept | CWIP | TWIP | Assessment |
|---------|------|------|------------|
| API number | `api10`, `api14` | `api10`, `apinum` | TWIP uses `apinum` (source field name); CWIP doesn't |
| Total depth | `total_depth_ft` | `total_dept` | CWIP suffixes with unit; TWIP preserves source abbreviation |
| Production | explicit (oil_bbl, gas_mcf) | explicit (oil_production_bbl, casinghead_gas_mcf) | TWIP more explicit |
| Timestamp | `ingest_batch_id` | `scraped_at` | Different semantics |

---

## 5. Location and Cross-Reference Divergences

### 5.1 File Location Comparison

| Content Type | CWIP Location | TWIP Location | Consistent? |
|-------------|---------------|---------------|-------------|
| Core docs | `docs/` | `docs/` | Yes |
| Audits | `docs/audits/` | `docs/audits/` | Yes |
| Business/strategy | `docs/business/` | `docs/business/` (empty) | Yes (structure) |
| Articles | `docs/articles/` | `docs/articles/` (empty) | Yes (structure) |
| Onboarding | `docs/onboarding/` | `docs/onboarding/` (empty) | Yes (structure) |
| Papers | `docs/papers/` | `docs/papers/` (empty) | Yes (structure) |
| Content pipeline | `docs/content/` | (not created) | **No** |
| Scoping docs | `docs/business/phase*.md` | `data/diagnostics/p-twip-001_*.md` | **No** |
| Diagnostic reports | `data/diagnostics/` (90 files) | `data/diagnostics/` (4 files) | Yes (structure) |
| Delivery docs | `data/delivery/docs/` (lost in P342) | (not created) | N/A |
| Buyer-facing PDFs | `data/output/_pdf_test/` | (not created) | **No** |
| QA companion tables | `data/delivery/cwip_qa_*.parquet` | `data/raw/twip_qa_*/` (in subdirs) | **No** — different path pattern |
| Raw data | `data/output/` (flat) | `data/raw/{table_name}/` (subdirs) | **No** — TWIP uses subdirs |

### 5.2 Cross-References

| Reference | CWIP | TWIP |
|-----------|------|------|
| CWIP references TWIP | No | N/A |
| TWIP references CWIP | N/A | Yes (`cross_state_comparison.md`, `operational_runbook.md`) |
| Runbook cross-references | Runbook references specific scripts and batch files | Runbook references `operational_runbook.md` commit hash for mirrored rules |
| Data dictionary references | Data inventory references QA reports and tables | Data dictionary references derivation prompts (e.g., "See P-TWIP-005") |
| Source inventory references | Sources documented inline in data inventory | Separate doc with cross-refs to fetcher scripts and ingestion scripts |

---

## 6. Reconciliation Recommendations

### Priority 1: Data Dictionary Format (HIGH IMPACT)

**Current state:**
- CWIP: 22-page branded PDF with Column | Type | Nulls | Description | Example
- TWIP: Markdown with Column | Type | Source/Description

**Recommendation:** Standardize on the CWIP PDF column schema (add Nulls and
Example columns to TWIP). TWIP's markdown is the source-of-truth; the PDF is
generated from it. Both products should:
1. Maintain a `docs/data_dictionary.md` as the editable source
2. Generate a branded PDF from it for buyer delivery
3. Use consistent column schema: Column | Type | Nulls | Description | Example

**CWIP action:** Create `docs/data_dictionary.md` as the markdown source for the
existing PDF.
**TWIP action:** Add Nulls and Example columns to `docs/data_dictionary.md`. Build
PDF generation pipeline.
**Scope:** Medium. CWIP needs markdown extraction from PDF; TWIP needs column additions.

### Priority 2: Source Inventory vs Data Inventory (MEDIUM IMPACT)

**Current state:**
- CWIP: Combined `cwip_data_inventory.md` (sources + tables + pipelines + relationships)
- TWIP: Separate `source_inventory.md` (sources only) + `data_dictionary.md` (tables)

**Recommendation:** TWIP's separation is cleaner. CWIP should adopt it:
- `source_inventory.md` — per-source metadata (URL, format, fetcher, status)
- `data_dictionary.md` — per-table column documentation
- `data_inventory.md` — high-level overview connecting sources to tables to pipelines

**Direction:** TWIP pattern is better. **Backport to CWIP.**
**Scope:** Medium. CWIP needs to decompose `cwip_data_inventory.md` into 2-3 files.

### Priority 3: QA Framework Formalization (MEDIUM IMPACT)

**Current state:**
- CWIP: Informal manual checklist (`cwip_manual_qa_checklist.md`)
- TWIP: Formal 3-level framework with companion table schema

**Recommendation:** TWIP's framework is more rigorous. CWIP should adopt the
three-level pattern and companion table schema.
**Direction:** TWIP pattern is better. **Backport to CWIP.**
**Scope:** Small. CWIP already has QA tables; needs the framework document.

### Priority 4: Table Naming Corrections (HIGH IMPACT, LOW EFFORT)

**Divergences requiring correction:**

| Issue | Fix | Where |
|-------|-----|-------|
| `cwip_production_monthly` missing `fact_` prefix | Rename to `cwip_fact_production_monthly` | CWIP |
| `operator_consolidation` / `operator_history` missing `twip_` prefix | Rename to `twip_dim_operator_consolidation`, `twip_dim_operator_history` | TWIP |
| `operator_registry` missing `twip_dim_` prefix | Rename to `twip_dim_operator_registry` | TWIP |
| `cwip_dim_inspections` should be `cwip_fact_inspections` | Reclassify as fact table (events, not dimensions) | CWIP |

**Scope:** Small per rename, but requires downstream reference updates.

### Priority 5: Column Naming Standards (MEDIUM IMPACT)

**Recommendations:**
- Adopt unit suffixes consistently: `_ft`, `_bbl`, `_mcf` (CWIP pattern: `total_depth_ft`)
- TWIP should rename `total_dept` → `total_depth_ft` and cast to numeric
- Standardize ingestion timestamp column: choose `scraped_at` (TWIP) or `ingest_batch_id` (CWIP)
  - Recommendation: `scraped_at` is clearer and self-documenting. Backport to CWIP.
- Source provenance: CWIP's `source_system` + `source_row_hash` pattern is richer.
  TWIP should adopt it alongside `source_file`.

**Scope:** Medium. Requires column renames and type casts.

### Priority 6: Scoping Doc Location (LOW IMPACT)

**Current state:**
- CWIP: `docs/business/phase*.md`
- TWIP: `data/diagnostics/p-twip-001_*.md`

**Recommendation:** Standardize on `docs/scoping/` for both products.
Scoping docs are documentation, not data or diagnostics.
**Scope:** Small. File moves only.

### Priority 7: Delivery Bundle Manifest (LOW IMPACT)

**Current state:**
- CWIP: Technical delivery architecture in `docs/business/`
- TWIP: Buyer-facing manifest in `docs/`

**Recommendation:** Both products need both:
1. `docs/delivery_bundle_manifest.md` — buyer-facing (coverage, tables, pricing)
2. `docs/business/delivery_architecture.md` — internal technical (S3, watermarking)

**Scope:** Small. CWIP needs a buyer-facing manifest; TWIP will need technical
architecture when delivery infrastructure is built.

### Priority 8: Buyer-Facing PDF Generation (FUTURE)

CWIP has a PDF generation pipeline (data dictionary, data inventory, getting
started guide, methodology). TWIP has none. When TWIP approaches delivery
readiness, the PDF generation pipeline should be shared/templated across both
products with per-product content.

**Scope:** Deferred until TWIP delivery readiness.

---

## 7. Reconciliation Sequence

| Step | Action | Repo | Priority |
|------|--------|------|----------|
| 1 | Fix unprefixed TWIP table names (operator_consolidation, operator_history, operator_registry) | TWIP | P4 |
| 2 | Add `fact_` prefix to `cwip_production_monthly` | CWIP | P4 |
| 3 | Reclassify `cwip_dim_inspections` → `cwip_fact_inspections` | CWIP | P4 |
| 4 | Add Nulls + Example columns to TWIP data dictionary | TWIP | P1 |
| 5 | Create `docs/data_dictionary.md` in CWIP (extract from PDF) | CWIP | P1 |
| 6 | Create `docs/source_inventory.md` in CWIP (decompose from data_inventory) | CWIP | P2 |
| 7 | Create `docs/qa_framework.md` in CWIP (formalize from manual checklist) | CWIP | P3 |
| 8 | Rename `total_dept` → `total_depth_ft` in TWIP | TWIP | P5 |
| 9 | Move scoping docs to `docs/scoping/` in both repos | Both | P6 |
| 10 | Create `docs/delivery_bundle_manifest.md` in CWIP | CWIP | P7 |
| 11 | Build shared PDF generation pipeline | Both | P8 |

**Owner decides which steps to execute, in what order, and whether CWIP
backports happen before or after TWIP reconciliation.**
