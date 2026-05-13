# TWIP Delivery Bundle Manifest

*Last updated: 2026-05-13*
*Status: Pre-delivery — tables in data/raw/ layer, not yet promoted to delivery*

---

## Product Description

The Texas Well Intelligence Platform (TWIP) is a structured dataset covering every oil, gas, injection, and disposal well registered with the Texas Railroad Commission. It mirrors the architecture of the Colorado Well Intelligence Platform (CWIP) with Texas-specific extensions for lease-level production, the dual API/lease key system, and RRC district structure.

## Coverage

| Dimension | Value |
|---|---|
| State | Texas |
| Total wells | 1,154,953 |
| Total leases | 298,879 |
| Operators | 74,947 |
| Production records | 1,625,955 lease-month rows |
| Inspections | 3,867,246 |
| Drilling permits | 948,729 |
| Hearings/dockets | 5,055,787 |
| Operator tenure transitions | 1,133,044 |
| Well-lease crosswalk pairs | 1,079,625 |

## Tables (Current State)

| Table | Rows | Layer | Description |
|---|---|---|---|
| twip_well_master | 1,154,953 | Master | One row per api10. Intrinsic well properties. |
| twip_fact_well_completions | 1,400,904 | Fact | One row per (api10, gas_rrcid). Completion events. |
| twip_fact_production_monthly | 1,625,955 | Fact | Lease-level monthly oil/gas production (EBCDIC source). |
| twip_fact_inspections | 3,867,246 | Fact | RRC inspection events with violation flags. |
| twip_dim_operator_registry | 74,947 | Dimension | RRC P-5 operator registrations. |
| twip_dim_drilling_permits | 948,729 | Dimension | Drilling permit records. |
| twip_dim_hearings | 5,055,787 | Dimension | RRC hearing/docket records. |
| twip_dim_operator_history | 1,133,044 | Dimension | Operator tenure per well (derived from completions). |
| twip_dim_well_lease_crosswalk | 1,079,625 | Dimension | api10 to lease_name mapping with effective dates. |
| twip_dim_injection_uic | 19 | Dimension | Injection/disposal well permits (subset; full run pending). |

## Known Limitations

1. **Production at lease level.** Texas reports production per lease, not per well. The well-lease crosswalk enables approximate per-well allocation, but true well-level production requires RRC Schedule A data (partially digitized, future work).

2. **Bond data and pipeline permits** are not available on the RRC standard downloads page. Source acquisition for these is ongoing.

3. **GIS shapefiles** are downloaded but not yet ingested into the Parquet delivery layer.

4. **api10 format:** "42" + 8-digit RRC apinum. api14 (with sequence/drillhole) is not available from this source.

5. **EBCDIC production data:** Volumes are decoded from COMP-3 packed decimal. Implied decimal places are not documented in PDA001 — values are whole integers (BBL, MCF).

## Pricing

$3,999/year per state. Separate subscription from CWIP (Colorado).
