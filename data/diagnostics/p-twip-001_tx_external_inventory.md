# P-TWIP-001 — Texas External Data Source Inventory

Generated: 2026-05-11

---

## Summary

12 Texas-specific external sources identified across 5 agencies (TCEQ, GLO, TWDB, BLM-NM, and state data portals). 3 Tier 1 (build with launch), 4 Tier 2/3 (build on demand), 5 defer/skip.

---

## TCEQ (Texas Commission on Environmental Quality)

### 1. Point Source Emissions Inventory (PSEI)

| Field | Detail |
|-------|--------|
| Agency | TCEQ |
| URL | https://www.tceq.texas.gov/airquality/point-source-ei ; Open Data: https://data.tceq.texas.gov/ |
| Format | Bulk CSV (annual); Socrata API |
| Est. Rows | 50-80K active air permits; O&G subset ~15-25K |
| Cadence | Annual |
| Key Fields | RN (Regulated Entity Number), CN, permit number, SIC/NAICS, authorized emissions by pollutant, lat/lon |
| Barriers | Low — bulk download available |
| CO Equivalent | CDPHE APEN (P267) |
| Priority | **HIGH — Tier 1** |
| Build Est. | 2-3 days |

### 2. Enforcement Actions

| Field | Detail |
|-------|--------|
| URL | https://www15.tceq.texas.gov/crpub/ (Central Registry) |
| Format | Central Registry web query; some data on Open Data portal; order text as PDF |
| Est. Rows | ~3-5K orders/year; O&G subset ~500-1K/year |
| Barriers | Medium-high — no clean bulk download for enforcement details |
| Priority | Medium — Tier 3 |
| Build Est. | 3-5 days |

### 3. Surface Water Quality Monitoring (SWQM)

| Field | Detail |
|-------|--------|
| URL | https://www.tceq.texas.gov/waterquality/monitoring/swqm-data |
| Format | Downloadable CSV; also via EPA Water Quality Portal |
| Est. Rows | 20M+ analytical results; O&G-relevant subset 2-5M |
| Barriers | Low — bulk download available |
| Priority | Medium — Tier 3 |
| Build Est. | 2-3 days |

### 4. TCEQ Open Data Portal

| Field | Detail |
|-------|--------|
| URL | https://data.tceq.texas.gov/ (Socrata-based) |
| Format | CSV, JSON, SODA API |
| Est. Rows | ~30+ datasets; priority: emissions inventory, compliance history |
| Barriers | Low — true open data with API |
| Priority | Medium — Tier 2 |
| Build Est. | 1-2 days |

### 5. UIC (non-Class II)

Note: Class II injection wells (O&G disposal) are RRC jurisdiction in Texas, not TCEQ. TCEQ handles Class I/III/IV/V only (~2-3K permits). Lower priority.

---

## GLO (Texas General Land Office)

### 6. State Mineral Leases

| Field | Detail |
|-------|--------|
| Agency | GLO |
| URL | https://gisweb.glo.texas.gov/glomapjs/ (GIS viewer); ArcGIS REST services |
| Format | ArcGIS REST + pagination |
| Est. Rows | ~15-20K state mineral leases; GLO manages ~13M acres of state mineral estate |
| Cadence | Monthly lease sales; annual royalty reports |
| Key Fields | Lease number, tract ID, lessee, bonus, royalty rate (typically 25%), acreage, county, effective/expiration date |
| Barriers | Medium-high — GIS viewer supports queries but not full bulk export. Lease sale results as PDFs |
| CO Equivalent | CO SLB (P282) |
| Priority | **HIGH — Tier 1** |
| Build Est. | 4-6 days |

### 7. GLO Production/Revenue Reports

Aggregate only (per-lease detail requires TPIA request). Low standalone value — well-level production comes from RRC. GLO value-add is lease context (royalty rates, terms).

---

## TWDB (Texas Water Development Board)

### 8. Groundwater Database (GWDB)

| Field | Detail |
|-------|--------|
| Agency | TWDB |
| URL | https://www.twdb.texas.gov/groundwater/data/gwdbrpt.asp |
| Format | Downloadable Access database (.mdb); CSV via web query |
| Est. Rows | ~140K+ water well records; ~500K+ water level measurements; ~200K+ water quality analyses |
| Cadence | Monthly (levels); annual (comprehensive update) |
| Key Fields | State well number, lat/lon, county, aquifer, total depth, water level (date + depth-to-water), water quality (TDS, chlorides, sulfates, pH) |
| Barriers | Low — bulk Access DB downloadable |
| CO Equivalent | USGS NWIS (P280) — TWDB is MORE comprehensive for TX than NWIS |
| Priority | **HIGH — Tier 1** |
| Build Est. | 3-4 days |

### 9. Water Rights

Fragmented across TCEQ (surface water, ~6-8K permits) and ~100 independent Groundwater Conservation Districts (no statewide aggregation). Medium priority, structural complexity.

---

## BLM (West Texas Federal Minerals)

### 10. BLM West Texas Leases

| Field | Detail |
|-------|--------|
| Agency | BLM New Mexico State Office (covers TX federal minerals) |
| Format | MLRS web lookup; GIS services (same issues as CO — P263) |
| Est. Rows | ~2-5K active federal leases; ~500K federal mineral acres |
| Barriers | Same as Colorado — MLRS no bulk download; GIS endpoints unreliable |
| Priority | Medium — Tier 2 |
| Build Est. | 4-6 days |

---

## State Data Portals

### 11. TNRIS (Texas Natural Resources Information System)

| Field | Detail |
|-------|--------|
| Agency | TWDB/TNRIS |
| URL | https://data.tnris.org/ |
| Format | GIS (Shapefile, GeoTIFF); free bulk download |
| Relevance | Reference/context: county boundaries, roads, geology, floodplain |
| Priority | Medium — Tier 2 |
| Build Est. | 1-2 days |

### 12. Texas Comptroller (Severance Tax)

Aggregate revenue data only on data.texas.gov. Operator-level tax data is confidential (Texas Tax Code Chapter 111). Same finding as Colorado DOR — not feasible for operator-level integration. **Skip.**

---

## Priority Matrix

| Tier | Source | Build Days | Rationale |
|------|--------|-----------|-----------|
| **1** | TWDB Groundwater DB | 3-4 | Direct NWIS equivalent; bulk downloadable |
| **1** | TCEQ Emissions Inventory | 2-3 | Direct APEN equivalent; bulk downloadable |
| **1** | GLO State Mineral Leases | 4-6 | Direct CO SLB equivalent; ArcGIS REST pattern |
| 2 | TCEQ Open Data Portal | 1-2 | Socrata API — fast, structured |
| 2 | TNRIS GIS layers | 1-2 | Spatial context reference |
| 2 | BLM West Texas | 4-6 | Same issues as CO |
| 3 | TCEQ Enforcement | 3-5 | Scraping complexity |
| 3 | TWDB Surface Water Quality | 2-3 | Large dataset, niche audience |
| Skip | Comptroller severance tax | — | Confidential at operator level |
| Skip | TPWD wildlife | — | Requires data agreement, niche |
| Skip | GLO Coastal Zone | — | Gulf Coast only, PDF-heavy |

---

## Key Differences from Colorado External Sources

1. **Scale:** Texas external sources are 3-5x larger by row count.
2. **TCEQ vs CDPHE:** TCEQ has better data infrastructure (Socrata portal) than CDPHE. Central Registry requires scraping for permit-level detail.
3. **Water data richer:** TWDB Groundwater Database is more comprehensive than USGS NWIS alone for Texas (mandatory drillers' reports).
4. **GLO much larger than CO SLB:** 13M acres vs 2.8M acres of state mineral estate.
5. **Fragmented groundwater governance:** ~100 independent GCDs with no statewide aggregated groundwater rights database.
6. **Class II injection is RRC, not TCEQ:** Injection well data comes with primary RRC integration, not as an external source.
