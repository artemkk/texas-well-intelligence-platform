# P-TWIP-001 — Texas Well Intelligence Platform Phase Scoping

Generated: 2026-05-11

---

## Phase 1 — RRC Core Regulatory

### Inventory Summary

| # | Source | Format | Est. Rows | Access | Build Days |
|---|--------|--------|-----------|--------|-----------|
| 1 | Well Registry (og_well_completion) | Fixed-width ZIP | ~1M completions | Free bulk DL | 5-8 |
| 2 | Production (lease-level) | Fixed-width ZIP | 50-100M lease-months | Free bulk DL | 8-12 |
| 3 | GIS Well Locations | Shapefile/REST | 1M+ points | Free DL | 3-5 |
| 4 | Operator Registry (P-5) | Fixed-width ZIP | ~35K operators | Free bulk DL | 2-3 |
| 5 | Drilling Permits (W-1) | Fixed-width ZIP | 1M+ historical | Free bulk DL | 3-5 |
| 6 | Completion Reports (W-2/G-1) | Fixed-width ZIP | ~1M completions | Free bulk DL | 5-8 |
| 7 | Plugging Records (W-3) | Fixed-width ZIP | ~500K plugged | Free bulk DL | 3-5 |
| 8 | Injection/Disposal (H-15/UIC) | Fixed-width ZIP | ~55K wells | Free bulk DL | 3-5 |
| 9 | Inspections & Enforcement | Fixed-width + PDF | Millions | Free (fragmented) | 5-8 |
| 10 | Bond Data (P-12) | Fixed-width ZIP | ~35K bonds | Free bulk DL | 2-3 |
| 11 | Operator History | Multi-file join | Millions | Free bulk DL | 5-8 |
| 12 | Spills / H-8 Complaints | Fragmented | 50-100K | Moderate (no bulk) | 8-15 |

**Total Phase 1 estimated effort: 53-85 build days**

### Recommended Build Order

**Tier 1 — Foundation (must-build-first, sequential):**
1. Well Registry — the master crosswalk (API ↔ lease key)
2. GIS Well Locations — spatial foundation
3. Operator Registry — operator join key
4. Production Data — core analytical dataset

**Tier 2 — Regulatory depth (can parallelize):**
5. Drilling Permits
6. Completion Reports (structured fields)
7. Plugging Records
8. Injection/Disposal Wells

**Tier 3 — Compliance and risk (can parallelize):**
9. Inspections & Enforcement
10. Bond Data
11. Operator History
12. Spills / H-8 Complaints

### Parallelization

Tier 1 is sequential (each builds on the previous). Tier 2 sources are independent — all 4 can run concurrently once Tier 1 is complete. Tier 3 sources are also independent of each other.

---

## Phase 2 — Document Extraction

### RRC Document Archive

The RRC imaging system contains 132M+ pages of scanned regulatory documents (TIFF/PDF). This is ~37x the volume of Colorado's Laserfiche archive (3.6M documents). Access is free but individual-document-retrieval only — no bulk download API.

### OCR / Parsing Opportunities

| Document Type | TX Form | CO Equivalent | Est. Documents | OCR Value |
|---|---|---|---|---|
| Completion reports | W-2 / G-1 | Form 5 | ~1M | HIGH — IP test data, perforations, casing |
| Plugging records | W-3 | Form 6 | ~500K | HIGH — plug details, cement, restoration |
| Drilling permits | W-1 | Form 2 | ~1M+ | MEDIUM — already well-structured |
| Injection well monitoring | H-10 | Bradenhead/MIT | ~55K/year | HIGH — injection volumes, pressures |
| Correspondence | Various | Correspondence | TBD | MEDIUM — regulatory letters |

### Well Log Library

The RRC physical log library holds logs for ~500K+ wells. Digital availability is partial (modern wells have LAS; older wells are paper scans). This is equivalent to CWIP's well log digitization roadmap item but at 5-10x scale.

### Estimated Document Volume and Storage

At 132M pages, assuming ~50KB/page average for TIFF: ~6.5 TB raw storage. Compressed: ~2-3 TB. OCR text output: ~200-500 GB. This requires cloud storage from day one (S3 or equivalent), not local disk.

---

## Phase 3 — External Sources

### Reusable Federal Pipelines (10 of 12 extend from CWIP)

| Pipeline | Change Level | Est. TX Rows |
|----------|-------------|-------------|
| FracFocus | Filter only | 2-2.5M |
| EIA DPR | None (already loaded) | ~3K |
| USGS Earthquakes | Filter + pagination | 5-15K |
| Census County | Filter only | 254 |
| BLM Statistics | Filter only | ~10 |
| EPA GHGRP | Filter only | 40-70K |
| EPA TRI | Filter + moderate restructure | 100-200K |
| EPA ECHO | Filter only | 50-100K |
| EPA SDWIS | Filter only | 100-150K |
| EIA Form 914 | None (already downloaded) | 8-12K |
| USGS NWIS | Filter + chunking | 1M+ |
| USGS Formation Tops | **Full redesign** | N/A |

**Federal pipeline extension effort: ~5-10 days** for the 10 filter-change pipelines. Formation tops requires a separate approach.

### Texas-Specific State Sources

| Source | Agency | Build Days | Priority |
|--------|--------|-----------|----------|
| TWDB Groundwater DB | TWDB | 3-4 | Tier 1 |
| TCEQ Emissions Inventory | TCEQ | 2-3 | Tier 1 |
| GLO State Mineral Leases | GLO | 4-6 | Tier 1 |
| TCEQ Open Data Portal | TCEQ | 1-2 | Tier 2 |
| TNRIS GIS layers | TWDB | 1-2 | Tier 2 |
| BLM West TX | BLM | 4-6 | Tier 2 |
| TCEQ Enforcement | TCEQ | 3-5 | Tier 3 |
| TWDB Water Quality | TCEQ/TWDB | 2-3 | Tier 3 |

**TX-specific source effort: ~22-31 days** for Tiers 1-3.

---

## Comparison Table — CWIP vs TWIP

| CWIP Table | TWIP Equivalent | Data Source | Ports Trivially? |
|---|---|---|---|
| cwip_well_master | twip_well_master | RRC og_well_completion + GIS | No — dual key system (API + lease) |
| cwip_production_monthly | twip_production_monthly | RRC lease-cycle data | **No — lease-level, not well-level** |
| cwip_dim_drilling_permits | twip_dim_drilling_permits | RRC W-1 permits | Yes (different parser, same concept) |
| cwip_fact_form5_extracted | twip_fact_completion | RRC W-2/G-1 structured | Yes (different parser) |
| cwip_fact_form6_ocr | twip_fact_plugging | RRC W-3 structured | Yes |
| cwip_dim_inspections | twip_dim_inspections | RRC violations/inspections | Partial (fragmented source) |
| cwip_dim_bradenhead | twip_dim_injection_monitoring | RRC H-10/H-15 | Different schema |
| cwip_dim_operator_history | twip_dim_operator_history | RRC operator + lease files | More complex (multi-join) |
| cwip_dim_bonds | twip_dim_bonds | RRC P-12 bonds | Yes |
| cwip_fact_fracfocus | twip_fact_fracfocus | FracFocus (filter change) | **Yes** |
| cwip_ref_formation_tops | twip_ref_formation_tops | TBD (no USGS equivalent) | **No — needs new source** |
| cwip_ref_earthquakes | twip_ref_earthquakes | USGS (filter change) | **Yes** |
| cwip_ref_census | twip_ref_census | Census (filter change) | **Yes** |
| cwip_ref_epa_* | twip_ref_epa_* | EPA (filter changes) | **Yes** |

**Summary:** 8 of 14 core table types port with parser changes or filter changes. 2 require structural redesign (production granularity, formation tops). 4 require new infrastructure (dual key system, lease-level production, operator history reconstruction, fragmented inspections).

---

## Build Sequencing Recommendation

### Phase 1 MVP — Minimum Viable TWIP

**Target:** Reach 50M+ rows across ~15 tables to match CWIP's Phase 1 scope.

**Priority sources (build in this order):**
1. Well Registry + GIS (foundation) — 8-13 days
2. Operator Registry — 2-3 days
3. Production Data — 8-12 days
4. Drilling Permits — 3-5 days
5. Completion Reports (structured) — 5-8 days

**MVP subtotal: 26-41 days, yielding ~55M+ rows across 5-6 tables**

### Phase 1 Extension

6. Plugging Records — 3-5 days
7. Injection/Disposal Wells — 3-5 days
8. Inspections — 5-8 days
9. Bond Data — 2-3 days
10. Operator History — 5-8 days

**Full Phase 1: 44-70 days, ~100M+ rows across 10-12 tables**

### Phase 3 Quick Wins (can run parallel to Phase 1)

Federal pipeline extensions (filter changes): 5-10 days
TX-specific Tier 1 sources (TWDB, TCEQ PSEI, GLO): 10-13 days

### Estimated Calendar Time to MVP

At 4 hours/day dedicated build time:
- MVP (5 core tables): 7-10 weeks
- Full Phase 1 (12 tables): 11-18 weeks
- Phase 3 quick wins: +2-3 weeks (parallelizable)

At 8 hours/day (full-time sprint):
- MVP: 4-5 weeks
- Full Phase 1: 6-9 weeks

---

## Risks and Open Questions

### 1. Lease-level production (CRITICAL)

Texas reports production at the lease level, not the well level. A lease can have 1-100+ wells. Well-level allocation (Schedule A of Form PR) has been partially digitized since ~2013 but coverage is incomplete.

**Risk:** Without well-level production, per-well and per-foot productivity analysis (the core of CWIP's analytical value) is limited to single-well leases or requires allocation models.

**Mitigation:** (a) Verify current Schedule A digitization coverage from RRC — if it has improved since 2023, the problem may be partially solved. (b) For multi-well leases without allocation, use lease-level production ÷ well count as a rough allocation. (c) Accept lease-level granularity for initial MVP and pursue well-level as an enhancement.

### 2. Dual key system

RRC uses both API numbers and District+Lease+Well composite keys. Many datasets are keyed by lease, not API. The crosswalk between these systems must be built and maintained.

**Risk:** Broken crosswalk means orphaned records — wells without production, production without wells.

**Mitigation:** Build the crosswalk as the FIRST pipeline step. og_well_completion contains both keys. Test crosswalk completeness before building downstream tables.

### 3. Fixed-width parsing

RRC bulk downloads use mainframe-era fixed-width text with published record layouts (PDF data dictionaries). Each file has a unique column-position specification.

**Risk:** Record layout changes (field widths, new fields) break parsers silently. RRC does not version-control record layouts.

**Mitigation:** Build parsers with explicit column-position configs (not regex). Add row-count and field-distribution sanity checks. Archive the record layout PDFs as parser documentation.

### 4. Scale (8x Colorado)

Texas has ~1M+ wells vs Colorado's 124K. Production data is 50-100M rows vs CWIP's 18M. Document archive is 132M pages vs 3.6M.

**Risk:** Processing time, storage costs, and checkpoint complexity all scale.

**Mitigation:** Cloud storage (S3) from day one. Checkpoint-based pipelines (proven pattern from CWIP). Basin-scoped initial builds (start with Permian only, then expand to Eagle Ford, Haynesville).

### 5. Formation tops data gap

No USGS-equivalent gridded formation model exists for Texas basins. Formation data must come from completion reports (text descriptions, not elevations) or commercial sources.

**Risk:** Subsurface geological context is unavailable at CWIP quality for TX.

**Mitigation:** Parse formation names from W-2/G-1 completion records. Accept text-based formation identification (Wolfcamp, Bone Spring, Eagle Ford) without precise elevation mapping. Explore Texas Bureau of Economic Geology publications for basin-level structure maps.

### 6. Texas open data policies

Texas Public Information Act (TPIA) governs access to government records. O&G regulatory data is overwhelmingly public. Confidential fields: operator financial data (tax), complainant identity (H-8), some proprietary geological data. No access barriers anticipated for the sources inventoried here.

### 7. RRC system modernization

The RRC has been actively modernizing its data systems. Fixed-width downloads may migrate to CSV/API. The Texas Open Data portal (data.texas.gov) may gain new RRC datasets. Verify current file formats and availability before building parsers.

### 8. Basin-scoping decision

Texas has multiple major basins: Permian (Midland + Delaware), Eagle Ford, Haynesville, Barnett, Anadarko (TX Panhandle), East Texas. CWIP covers a single basin (DJ). TWIP should either:
- Cover all TX basins (maximum scope, maximum value, maximum effort)
- Start with Permian only (highest commercial value, fastest to MVP)
- Start with Permian + Eagle Ford (two largest, covers most buyer demand)

**Recommendation:** Start with Permian. It's the highest-activity basin, the most commercially relevant, and the one the validated early adopter (former colleague) operates in. Expand to Eagle Ford and Haynesville in Phase 1 Extension based on subscriber demand.
