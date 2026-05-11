# P-TWIP-001 — Texas Railroad Commission Data Source Inventory

Generated: 2026-05-11

---

## Summary

16 RRC data source categories identified. Primary access method: monthly bulk downloads of fixed-width text files from https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/. Online query via PDQ (Production Data Query) system. 132M+ pages of scanned documents in RRC imaging system.

---

## Critical Architecture Differences: Texas vs Colorado

1. **Lease-level vs well-level production.** Colorado reports production per well. Texas reports per lease. Multi-well lease allocation is the key technical challenge.
2. **Dual key system.** Texas uses both API numbers AND District+Lease+Well composite keys. Many bulk datasets are keyed by the lease system. Colorado uses API exclusively.
3. **12 district offices.** RRC operations distributed across 12 districts. Colorado has a single statewide ECMC system.
4. **Scale.** Texas: ~1M+ wells, ~350K active. Colorado: ~124K wells. Texas is ~8x larger by well count.
5. **Fixed-width format.** Bulk downloads use mainframe-era fixed-width text with published record layouts, not CSV.
6. **Document imaging.** Texas uses a custom imaging system with TIFF/PDF scans (132M+ pages). Colorado uses Laserfiche (~3.6M documents).

---

## Source-by-Source Inventory

### 1. Well Registry (og_well_completion)

| Field | Detail |
|-------|--------|
| URL | https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/ |
| Format | Fixed-width text in ZIP |
| Est. Rows | ~1,000,000+ completions |
| Cadence | Monthly |
| Key Fields | API (42-XXX-XXXXX), District+Lease+Well composite key, operator number, county, field, well type, status, lat/lon, total depth, completion/plug dates |
| Barriers | None — free bulk download |
| Build Est. | 5-8 days |

### 2. Production Data (lease-level)

| Field | Detail |
|-------|--------|
| Files | OG_LEASE_CYCLE_DISP_DATA, OG_FIELD_DW_DATA |
| Format | Fixed-width text in ZIP |
| Est. Rows | 50-100M lease-month records (digital back to 1993) |
| Cadence | Monthly (2-3 month lag for stabilization) |
| Key Fields | District, lease number, operator number, field, month, oil (BBL), casinghead gas (MCF), gas well gas (MCF), condensate, water, days producing, well count |
| Barriers | None — free bulk download. Lease-level granularity (not well-level) is the major structural issue |
| Build Est. | 8-12 days |

### 3. Drilling Permits (W-1)

| Field | Detail |
|-------|--------|
| File | OG_DRILLING_PERMIT |
| Query | https://webapps.rrc.texas.gov/DPA/queryAction.do |
| Format | Fixed-width text in ZIP (bulk); HTML (online, updated daily) |
| Est. Rows | 1M+ historical; ~80-100K/year recent |
| Cadence | Monthly (bulk), daily (online) |
| Key Fields | Permit number, API, district, lease, operator, county, field, permit type (new/recompletion/re-entry), date, total depth, well type, surface location |
| Barriers | None. Older permits lack lat/lon (use survey-line distances) |
| Build Est. | 3-5 days |

### 4. Completion Reports (W-2 / G-1)

| Field | Detail |
|-------|--------|
| File | OG_WELL_COMPLETION (structured fields) + scanned docs via imaging |
| Format | Fixed-width text (structured); TIFF/PDF (scanned originals) |
| Est. Rows | ~1M+ completions |
| Key Fields | API, completion date, total depth, perforations, IP test (BOPD/MCFD/BWPD), choke, pressures, formation, casing program, cement data |
| Barriers | None for structured data. Scanned docs: individual retrieval only, no bulk download API |
| Build Est. | 5-8 days (structured); months (OCR equivalent to CWIP Phase 2) |

### 5. Plugging Records (W-3 / W-3A)

| Field | Detail |
|-------|--------|
| Format | Plug date/depth fields in OG_WELL_COMPLETION; scanned W-3 docs via imaging |
| Est. Rows | ~500K+ plugged wells historically |
| Key Fields | API, plug date, plug depth, plugging operator, well status, cement plugs, casing left |
| Barriers | None for structured. Scanned docs: individual retrieval |
| Build Est. | 3-5 days |

### 6. Operator Registry (P-5 / P-4)

| Field | Detail |
|-------|--------|
| File | OG_OPERATOR_DATA |
| Query | https://webapps.rrc.texas.gov/OGP5/OGP5QueryAction.do |
| Format | Fixed-width text in ZIP |
| Est. Rows | ~30-40K registered operators |
| Key Fields | Operator number, name, P-5 status, organization type, address, districts, authorized representative |
| Barriers | None |
| Build Est. | 2-3 days |

### 7. Inspections & Enforcement

| Field | Detail |
|-------|--------|
| File | OG_VIOLATION_DATA (verify current availability) |
| Format | Fixed-width text (bulk); HTML (online); PDF (Commissioner orders) |
| Est. Rows | ~100K+ inspections/year; millions historically |
| Key Fields | Inspection date, inspector, district, lease, operator, type, violation Y/N, violation code, corrective action, penalty |
| Barriers | Low-moderate. Bulk violation file availability inconsistent. Commissioner orders are PDFs. Fragmented across inspection records, violations, orders. |
| Build Est. | 5-8 days |

### 8. Spills / H-8 Complaints

| Field | Detail |
|-------|--------|
| Format | Fragmented across district offices and Oil Field Cleanup database |
| Est. Rows | 50-100K+ historical |
| Barriers | Moderate — no consolidated bulk download. May require TPIA (Public Information Act) requests |
| Build Est. | 8-15 days |

### 9. Bond Data (P-12)

| Field | Detail |
|-------|--------|
| Format | Fields in OG_OPERATOR_DATA; possible separate OG_BOND_DATA file |
| Est. Rows | ~30-40K bond records |
| Key Fields | Bond number, operator, bond type (individual/blanket), amount, surety, status |
| Barriers | Low |
| Build Est. | 2-3 days |

### 10. Operator History

| Field | Detail |
|-------|--------|
| Format | Multi-file join: OG_OPERATOR_DATA + OG_REGULATORY_LEASE |
| Est. Rows | Millions (lease-level operator assignments) |
| Barriers | None — complexity is in join logic, not access |
| Build Est. | 5-8 days |

### 11. GIS / Shapefiles

| Field | Detail |
|-------|--------|
| URL | https://gis.rrc.texas.gov/GISViewer/ |
| Format | Shapefiles, KML, ArcGIS REST |
| Est. Features | 1M+ well points; 8K+ field boundaries; district boundaries; pipeline network |
| Barriers | None — free download |
| Build Est. | 3-5 days |

### 12. Formation Tops / Well Logs

| Field | Detail |
|-------|--------|
| Format | LAS (partial digitization); TIFF paper scans; formation names in completion records |
| Est. Volume | 500K+ wells in physical library |
| Barriers | Significant — partial digital availability; comprehensive data is commercial. No USGS-equivalent gridded model for TX basins |
| Build Est. | 15-30+ days (and requires alternative data source strategy) |

### 13. Injection/Disposal Wells (H-15 / UIC)

| Field | Detail |
|-------|--------|
| Format | Fixed-width text (bulk); queryable via PDQ |
| Est. Rows | ~55K+ Class II wells (largest UIC program in US) |
| Key Fields | API, permit number, well type (disposal/enhanced recovery), injection formation, max pressure/rate, annual volumes |
| Barriers | None |
| Build Est. | 3-5 days |

### 14. Pipeline Permits (T-4)

| Field | Detail |
|-------|--------|
| Format | Shapefiles (GIS) + fixed-width text |
| Est. Volume | 470K+ miles of regulated pipeline |
| Barriers | None |
| Build Est. | 5-8 days |

### 15. Document Imaging System

| Field | Detail |
|-------|--------|
| URL | https://webapps.rrc.texas.gov/CMPL/publicSearchAction.do |
| Format | TIFF/PDF scanned images |
| Est. Volume | 132M+ pages |
| Barriers | None for access; extreme volume for OCR. Individual document retrieval, no bulk API |

### 16. Hearings & Dockets

| Field | Detail |
|-------|--------|
| Format | PDF (examiner reports, orders); online query |
| Est. Rows | Thousands/year |
| Barriers | Low |
| Build Est. | 3-5 days |
