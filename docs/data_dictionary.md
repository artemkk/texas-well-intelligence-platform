# TWIP Data Dictionary

*Last updated: 2026-05-12*

---

## twip_fact_well_records_raw

Zero-skip preservation table. Every source row from the RRC Statewide API Data (.dbf files), including source-side duplicates. No dedup, no filtering.

| Column | Type | Source |
|--------|------|--------|
| api10 | str | Derived: "42" + apinum |
| apinum | str | RRC 8-digit API (county 3 + well 5) |
| abstract | str | Texas land abstract number |
| block | str | Survey block |
| completion | str | Completion date (YYYYMMDD) |
| field_name | str | RRC field name |
| lease_name | str | Lease name |
| gas_rrcid | str | RRC internal record ID |
| oil_gas_co | str | Oil/gas classification (O/G) |
| on_off_sch | str | On/off schedule indicator |
| operator | str | Operator name |
| permit_num | str | Drilling permit number |
| plug_date | str | Plug date (YYYYMMDD) |
| refer_to_a | str | API cross-reference |
| section | str | Survey section |
| survey | str | Survey name |
| total_dept | str | Total depth (ft) |
| wellid | str | Well identifier within lease |
| quadnum | str | Quadrangle number |
| source_file | str | Source .dbf filename |
| scraped_at | str | Ingestion timestamp (ISO 8601 UTC) |

---

## twip_well_master

One row per api10. Intrinsic well-as-physical-entity properties only. No derived "current" attributes (operator, field, status). Those require temporal reasoning across completion events and other sources.

**Primary key:** api10 (unique, 10-char str starting with "42")

| Column | Type | Description |
|--------|------|-------------|
| api10 | str | 10-digit Texas API (42 + county + well) |
| apinum | str | 8-digit API without state prefix |
| abstract | str | Texas land abstract number |
| block | str | Survey block |
| refer_to_a | str | API cross-reference |
| section | str | Survey section |
| survey | str | Survey name |
| total_dept | str | Total depth (ft) |
| quadnum | str | Quadrangle number |
| scraped_at | str | Ingestion timestamp |
| source_file | str | Source .dbf filename |

**Column classification rule:** A column is a WELL_PROPERTY if it varies in <1% of api10s with multiple source rows. All others are EVENT_PROPERTY and go to twip_fact_well_completions.

---

## twip_fact_well_completions

One row per (api10, gas_rrcid). Each row is a completion event — a well may have multiple completions into different formations with different operators over its lifetime.

**Primary key:** (api10, gas_rrcid)

| Column | Type | Description |
|--------|------|-------------|
| api10 | str | FK to twip_well_master |
| gas_rrcid | str | RRC internal completion record ID |
| operator | str | Operator at time of this completion |
| lease_name | str | Lease name |
| field_name | str | RRC field name (formation/reservoir) |
| oil_gas_co | str | O = oil, G = gas |
| on_off_sch | str | On/off schedule indicator |
| permit_num | str | Drilling permit number |
| completion | str | Completion date (YYYYMMDD) |
| plug_date | str | Plug date (YYYYMMDD) |
| wellid | str | Well identifier within lease |
| scraped_at | str | Ingestion timestamp |
| source_file | str | Source .dbf filename |

---

## twip_dim_operator_registry

One row per RRC operator number. From P-5 Organization Report data.

**Primary key:** operator_number (str, verbatim from RRC)

See P-TWIP-005 for full 41-column schema.

---

## twip_dim_operator_history

Empty. Populated in P-TWIP-015 from well-level operator transitions.

---

## twip_dim_operator_consolidation

Empty. Populated incrementally as M&A events surface.

---

## Notes

- **api10 derivation:** api10 = "42" + apinum (Texas state code + 8-digit county+well)
- **api14 not available** from this source (no sequence/drillhole digits in the .dbf)
- **All identifier columns stored as str**, preserved verbatim from source
- **No derived "current" attributes** on master at ingestion time
