# P-TWIP-001 — Federal Source Reuse Assessment

Generated: 2026-05-11

---

## Summary

12 CWIP federal pipelines assessed for Texas extension. 10 extend with filter-level or minor changes. 2 already contain TX data with zero code changes. 1 requires full redesign (USGS Formation Tops).

---

## Pipeline-by-Pipeline Assessment

| # | Pipeline | TX Present? | Change Level | Key Changes | Est. TX Rows |
|---|----------|------------|-------------|-------------|-------------|
| 1 | FracFocus | In raw data | **Filter only** | State filter "Colorado" → "Texas" in 2 files | 2-2.5M ingredient rows |
| 2 | USGS Formation Tops | **No** | **Full redesign** | No equivalent raster model for TX basins | N/A |
| 3 | EIA DPR | **Already loaded** | **None** | Permian, Eagle Ford, Haynesville already in output | ~3K rows (TX regions) |
| 4 | USGS Earthquakes | No | Filter + pagination | Bounding box change; may need temporal chunking for TX volume | 5-15K events |
| 5 | Census County | No | **Filter only** | STATE_FIPS "08" → "48" (254 TX counties) | 254 rows |
| 6 | BLM Statistics | In source Excel | **Filter only** | "colorado" → "texas"; expect sparse data | ~10 rows |
| 7 | EPA GHGRP | No | **Filter only** | "COLORADO" → "TEXAS" in URL | 40-70K rows |
| 8 | EPA TRI | No | Filter + moderate restructure | State filter swap for facilities; need 5 ZIP-prefix queries (75-79) for reporting form | 100-200K rows |
| 9 | EPA ECHO | No | **Filter only** | p_st=CO → p_st=TX; 5-10x more pagination pages | 50-100K facilities |
| 10 | EPA SDWIS | No | **Filter only** | "CO" → "TX" in 2 places | 100-150K violations |
| 11 | EIA Form 914 | **Already downloaded** | **None** | Parse already supports --state TX | 8-12K rows |
| 12 | USGS NWIS | No | Filter + chunking | stateCd=CO → TX; may need HUC-region chunking for large TX dataset | 1M+ daily values |

---

## Detail: Pipelines Requiring No or Minimal Changes

### EIA DPR (Pipeline 3) — Zero changes
Already loads all 7 DPR regions including Permian, Eagle Ford, and Haynesville. Output parquet already contains TX data. Just filter downstream.

### EIA Form 914 (Pipeline 11) — Zero changes
Download pulls all states. Parse supports `--state TX`. Only the reconciliation function (CO-specific cross-reference) needs modification for a TX well_master.

### FracFocus (Pipeline 1) — 3 lines changed
Change `--state` default from "Colorado" to "Texas" in parse script. Rename output file. TX is the #1 frac state — expect ~2-2.5M ingredient rows (~4x Colorado).

### Census (Pipeline 5) — 1 line changed
STATE_FIPS "08" → "48". TX has 254 counties vs CO's 64.

### BLM (Pipeline 6) — 1 string change
"colorado" → "texas" in text match. Expect sparse data — TX has minimal federal land.

### EPA GHGRP (Pipeline 7) — 1 string change
"COLORADO" → "TEXAS" in URL. TX has ~8-10x CO's O&G footprint.

### EPA ECHO (Pipeline 9) — 1 string change
p_st=CO → p_st=TX. Runtime 5-10x longer due to volume.

### EPA SDWIS (Pipeline 10) — 2 string changes
"CO" → "TX" in two fetch_all calls.

---

## Detail: Pipelines Requiring Moderate Changes

### USGS Earthquakes (Pipeline 4)
Replace Colorado bounding box (36.5-41.5°N, 109.5-101.5°W) with Texas box (25.8-36.5°N, 106.7-93.5°W). TX is much larger — may need temporal chunking or sub-regional queries to avoid 20K-event API limit. West TX induced seismicity (Delaware Basin) is significant.

### EPA TRI (Pipeline 8)
Facility table: simple state filter swap (state_abbr/CO → state_abbr/TX). Reporting form table: CO uses ZIP prefix "80"; TX spans 5 prefixes (75, 76, 77, 78, 79) — need 5 separate fetch_all calls and concatenation. Moderate code change.

### USGS NWIS (Pipeline 12)
stateCd=CO → stateCd=TX. TX groundwater network is 2-3x CO's. Daily values download may exceed NWIS API response limits — likely needs chunking by HUC region or time window. Note: TWDB Groundwater Database is MORE comprehensive for TX than NWIS and should be the primary water source.

---

## Detail: Pipeline Requiring Full Redesign

### USGS Formation Tops (Pipeline 2)
The CWIP pipeline samples USGS Denver Basin 3D Model rasters (24 ESRI grids in EPSG:5070). **No equivalent gridded model exists for any TX basin** (Permian, Eagle Ford, Haynesville). USGS has published resource assessments but not basin-wide formation-top raster surfaces.

**Alternative TX formation top data sources:**
- RRC completion reports: formation names in W-2/G-1 (text, not elevation data)
- Texas Bureau of Economic Geology: some structure maps (limited coverage)
- Commercial providers (IHS/Enverus): proprietary formation picks
- USGS National Produced Waters Geochemical Database: some formation info

**Verdict:** Formation tops for TX require a fundamentally different approach — likely point-based formation picks from completion reports rather than raster sampling. This is the hardest pipeline to extend.
