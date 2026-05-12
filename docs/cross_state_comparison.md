# CWIP vs TWIP: Cross-State Architecture Comparison

*Last updated: 2026-05-12*

## Purpose

This document captures architectural and data-model differences between the Colorado Well Intelligence Platform (CWIP) and the Texas Well Intelligence Platform (TWIP). It serves subscribers who use both products, developers working on either repo, and the owner when prioritizing cross-state feature parity. Updated as architecture evolves.

---

## Quick Reference

| Dimension | CWIP (Colorado) | TWIP (Texas) |
|---|---|---|
| Regulator | ECMC (formerly COGCC) | Railroad Commission (RRC) |
| Wells | 124,064 | ~1M+ (not yet ingested) |
| Delivery tables | 72 | 3 (ingestion in progress) |
| Total rows | 54,757,197 | 74,947 (operator registry only) |
| Production granularity | Well-level | Lease-level |
| Primary well key | api10 | api10 + lease composite |
| Operator registry | De facto (union of 3 tables) | Standalone master (74,947 operators) |
| operator_number dtype | str (normalized P364) | str (from initial build) |
| Document archive | 4.17M docs (Laserfiche) | 132M+ pages (RRC imaging, not yet ingested) |
| Formation tops | USGS gridded model | No equivalent (major gap) |
| Source acquisition | HTTP/scraping | Playwright (MFT portal) |
| Delivery pipeline | LemonSqueezy → Lambda → SQS → Fargate → SES | Not yet built |
| Backbone | cwip_well_master (star schema) | twip_well_master (planned, same pattern) |

---

## Regulatory Landscape

### Colorado: ECMC

- **Jurisdiction:** Oil, gas, injection, disposal wells. Environmental oversight of O&G operations. Single statewide agency.
- **Reporting cadence:** Monthly production (Form 7). Permits, completions, inspections on event-driven basis.
- **Geographic structure:** Single statewide system. No district subdivision.
- **Data delivery:** COGIS web portal (scraping), bulk CSV downloads, Laserfiche document management system (structured, web-accessible).
- **Access:** Free, no authentication for most sources. No rate limits documented for bulk downloads.

### Texas: RRC

- **Jurisdiction:** Oil, gas, injection, disposal, pipeline safety. Broader scope than ECMC (includes pipelines and gas utilities).
- **Reporting cadence:** Monthly production (Form PR). Permits processed daily. P-5 organization report annual renewal.
- **Geographic structure:** 12 district offices (Districts 1-10, 7B/7C, 8/8A). Some data is district-partitioned.
- **Data delivery:** MFT portal (Managed File Transfer — requires browser session, no direct HTTP download). Fixed-width text files in mainframe-era format with published COBOL record layouts.
- **Access:** Free, no authentication for MFT downloads (browser session only). Online query system warns against automated scraping. Bulk downloads are the supported path.

### Key Contrast

ECMC data is more readily machine-accessible (web scraping, CSV downloads). RRC data requires browser automation (Playwright) for the MFT portal and fixed-width parsing per COBOL record layouts. RRC's scale is ~8x ECMC by well count.

---

## Data Model Differences

### Production Data Granularity

**CWIP:** One production row per well per month. Well-level analysis is direct — join cwip_production_monthly to cwip_well_master on api10/api_norm.

**TWIP:** One production row per LEASE per month. A lease can contain 1-100+ wells. Well-level analysis requires either:
- The lease-to-well crosswalk (maps lease → constituent wells) plus equal or proportional allocation
- RRC Schedule A data (well-level allocation within a lease, partially digitized since ~2013)
- Acceptance of lease-level granularity for multi-well lease analysis

**Implication:** Per-foot productivity analysis (article-01's core metric) requires well-level production. In TWIP, this is available only for single-well leases unless Schedule A allocation data is ingested.

### Key System

**CWIP:** api10 (10-digit API number) is the universal join key. Every table that references a well uses api10.

**TWIP:** Dual-key system.
- api10 for well identity (same as CWIP)
- District + Lease Number composite for lease/production identity
- Many RRC bulk datasets are keyed by the lease composite, not API
- The well-to-lease crosswalk (from og_well_completion) bridges the two key spaces

### Operator Registry

**CWIP:** No standalone operator master table. De facto registry via:
- cwip_well_master.operator_number (3,619 current operators)
- cwip_dim_operator_history (4,325 historical operators — strict superset)
- cwip_dim_operator_consolidation (4,303 operators with corporate family mapping)

**TWIP:** Standalone master at twip_dim_operator_registry (74,947 operators from RRC P-5 data). Includes P-5 status (active/inactive/delinquent), organization type, renewal dates, district authorizations, and full address data. This is a TWIP architectural improvement over CWIP — CWIP should backport this pattern.

### Consolidation Table

**CWIP:** Originally over-grouped (151 operators in one mega-family per P363 finding M2). P364 fix 5 rebuilt with discrete parent_operator_number + acquisition_date columns. Over-grouping still present in corporate_family field pending manual M&A review.

**TWIP:** Same improved schema from initial build. Empty pending population as M&A events surface.

### Document Imaging

**CWIP:** 4,176,054 documents indexed in cwip_fact_laserfiche_index. Laserfiche-based, structured metadata (doc_name, doc_type, api10, dates). OCR pipelines extract text from 11 document classes. Integrated into the 72-table delivery bundle.

**TWIP:** 132M+ pages in RRC imaging system (~37x CWIP's volume). Individual document retrieval via web interface. Phase 2 of TWIP build — not yet ingested. Document class structure differs from CO (W-2/G-1 completions vs Form 5, W-3 plugging vs Form 6, etc.).

### Formation Tops

**CWIP:** cwip_ref_formation_tops (2,775,468 rows) derived from USGS Denver Basin 3D geological model. Gridded raster surfaces for 24 formations. Well-level formation elevation lookups.

**TWIP:** No equivalent. USGS has no gridded formation model for Permian Basin, Eagle Ford, or Haynesville. Formation data comes from well completion records (text field naming the completed formation, not structured elevation data). This is the largest analytical gap between the two products.

### Backbone Architecture

Both use wells-as-backbone star schema. In CWIP, 44 of 72 tables FK to cwip_well_master via api10. TWIP will mirror this: twip_well_master as the central dimension table, with lease-to-well crosswalk handling the production join to lease-level data.

### Texas-Specific Dimensions

TWIP captures dimensions that have no CWIP equivalent:
- **RRC Districts** (12 districts as a first-class dimension — CO has no district system)
- **Lease Number** (RRC regulatory unit — CO doesn't use leases as a regulatory concept at this level)
- **P-5 Status** (active/inactive/delinquent with annual renewal dates — no CO equivalent)
- **Operator authorization by district** (operators authorized in specific RRC districts)

---

## Coverage Gaps and Additions

### What CWIP Has That TWIP Does Not (Yet)

| Category | CWIP State | TWIP State | TWIP Prompt |
|---|---|---|---|
| Well registry | 124,064 wells | Not yet ingested | P-TWIP-007 |
| Production data | 18.3M monthly rows | Not yet ingested | P-TWIP-009 |
| Drilling permits | 123,896 permits | Not yet ingested | P-TWIP-010 |
| Completion reports | 275,932 Form 5 docs | Not yet ingested | P-TWIP-011 |
| Inspections | 420,257 records | Not yet ingested | Future |
| Document OCR (Phase 2) | 11 pipelines, 1.8M+ rows | Not yet started | Phase 2 |
| Formation tops | 2.78M rows | Major gap — no equivalent source | Needs research |
| FracFocus | 557,551 rows | Not yet (filter change from CWIP) | Future |
| External sources (Phase 3) | 15 sources integrated | Not yet started | Future |
| Delivery pipeline | Full: webhook → Lambda → Fargate → SES | Not built | Future |
| Watermarking + PDF gen | Protected scripts, working | Not built | Future |
| Analytical articles | 4 articles (article-01 through 04) | None | Future |
| Onboarding video script | Documented, ready to record | None | Future |

### What TWIP Has That CWIP Does Not

| Category | TWIP State | CWIP State | Backport? |
|---|---|---|---|
| Standalone operator master | 74,947 operators | No standalone table | Yes — recommended |
| Playwright source automation | Working (MFT portal) | Not needed (ECMC is HTTP) | Useful for future sources |
| Improved consolidation schema | From initial build | Rebuilt in P364 fix 5 | Already done |
| Source provenance (source_meta.json) | Standard pattern | Ad hoc per pipeline | Recommend standardization |
| District dimension | 12 RRC districts | N/A (CO has none) | Not applicable |
| Lease dimension | First-class | N/A (CO is well-level) | Not applicable |
| P-5 status tracking | Active/inactive/delinquent | No equivalent | Not applicable |

---

## Backport Candidates

### TWIP → CWIP (CWIP gets TWIP improvements)

| Item | Scope | Currently Scheduled? |
|---|---|---|
| Standalone operator registry table (cwip_dim_operator_registry) | Medium (1-2 days) | Not yet |
| Source provenance standardization (source_meta.json pattern on every CWIP pipeline) | Small (per-pipeline) | Not yet |
| Playwright fetcher pattern (for any future CWIP source needing browser automation) | Small (as-needed) | Not yet |

### CWIP → TWIP (TWIP catches up to CWIP maturity)

| Item | Scope | Currently Scheduled? |
|---|---|---|
| Well registry ingestion | Large (5-8 days) | P-TWIP-007 |
| Production data ingestion | Large (8-12 days) | P-TWIP-009 |
| Drilling permits | Medium (3-5 days) | P-TWIP-010 |
| Completions (structured) | Medium (5-8 days) | P-TWIP-011 |
| All remaining Phase 1 sources | Large (total 44-70 days) | Queued per zero-skip rule |
| Document OCR (Phase 2) | Very large (months) | Future |
| Federal source pipelines (Phase 3) | Medium (5-10 days for filter changes) | Future |
| TX-specific external sources | Medium (22-31 days) | Future |
| Delivery pipeline (commerce) | Large (Fargate + SES + LemonSqueezy) | Future |
| Data dictionary + documentation | Medium | Future |

---

## Subscriber-Facing Implications

### What Works the Same in Both Products

- **Per-foot productivity analysis:** Both use well-level metrics. Join production to well_master, divide by lateral length. Same analytical pattern.
- **Operator FE analysis:** Both use operator_number (str) as join key. Same regression specification applies cross-state.
- **Spatial analysis:** Both have well lat/lon. CWIP from ECMC survey headers, TWIP from RRC GIS shapefiles.

### What Differs

- **Production queries:**
  - CO: `SELECT api10, oil FROM cwip_production_monthly WHERE api10 = '...'` — direct well-level
  - TX: `SELECT lease_number, district, oil FROM twip_production_monthly WHERE lease_number = '...'` — lease-level. For well-level, join through the well-lease crosswalk first.
- **Document scans:** Available in CWIP delivery bundle. Not yet available in TWIP.
- **Formation tops:** Available in CWIP (USGS model). Not available in TWIP (no equivalent source).
- **Pricing:** $3,999/year per state, separate subscriptions. Bundle pricing not yet established.

---

## Document Maintenance

This document updates as architecture evolves. Any prompt that changes either repo's architecture should update the relevant section here as part of its work. The document lives in the TWIP repo only (single source of truth). It is not duplicated in CWIP.
