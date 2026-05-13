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

Operator tenure transitions per well, derived from completion event sequences. 1,133,044 rows.

**Primary key:** (api10, operator_name, effective_date)

| Column | Type | Description |
|--------|------|-------------|
| api10 | str | FK to twip_well_master |
| operator_number | str | Empty (not available from completions source) |
| operator_name | str | Operator name at time of this tenure |
| effective_date | str | Completion date when this operator first appears |
| termination_date | str | Completion date when operator changes (null if current) |
| is_current | bool | True for most recent operator per api10 |
| lease_number | str | Lease name during this tenure |
| district | str | Empty (not derivable from completions) |
| scraped_at | str | Derivation timestamp |

---

## twip_dim_well_lease_crosswalk

Maps api10 to lease_name with effective dates. Enables lease-level production to join to the well backbone. 1,079,625 rows.

**Primary key:** (api10, lease_name)

| Column | Type | Description |
|--------|------|-------------|
| api10 | str | FK to twip_well_master |
| lease_name | str | RRC lease name |
| effective_date | str | First completion date for this (api10, lease) pair |
| termination_date | str | Last completion date (null if current) |
| is_current | bool | True for most recent lease per api10 |
| n_completions | int | Count of completions in this (api10, lease) pair |
| district | str | Empty (not derivable from completions) |
| scraped_at | str | Derivation timestamp |

---

## twip_fact_production_monthly

Lease-level monthly oil production from RRC Oil Tape (EBCDIC). 1,625,955 rows. Derived from type-03 Production Segment records with parent Root(01) and Cycle(02) context.

**Primary key:** (district, lease_number, rpt_cycle_key)

| Column | Type | Description |
|--------|------|-------------|
| district | str | RRC district code (01-14) |
| lease_number | str | RRC lease number (unique within district) |
| oil_code | str | "O" = oil lease |
| rpt_cycle_key | str | YYMM reporting period |
| oil_production_bbl | int | Barrels of oil produced (COMP-3 decoded) |
| casinghead_gas_mcf | int | MCF of casinghead gas produced (COMP-3) |
| casinghead_gas_lift | int | MCF of gas lift injected (COMP-3) |
| corrected_report_flag | str | N=original, Y=corrected |
| posting_year | str | Year production was posted to database |
| posting_month | str | Month posted |
| posting_day | str | Day posted |
| filed_by_edi | str | Y=electronically filed |
| oil_ending_balance | int | Oil in storage at end of month (COMP-3) |
| oil_allowable_cycle_bbls | int | Allowable for the cycle (COMP-3) |
| prod_month | str | Production month (derived from rpt_cycle_key) |
| prod_year | str | Production year (derived, 4-digit) |
| scraped_at | str | Ingestion timestamp |

**Source:** EBCDIC cp037 encoding, COMP-3 packed decimal (PIC S9(09) = 5 bytes). Decoded at ingestion.

---

## twip_fact_inspections

RRC inspection events with violation and compliance data. 3,867,246 rows.

| Column | Type | Description |
|--------|------|-------------|
| operator_name | str | Operator name |
| p5_operator_no | str | P-5 operator number |
| district | str | RRC district |
| district_office_inspecting | str | District office conducting inspection |
| oil_lease_gas_well_id | str | Lease/well identifier |
| lease_fac_name | str | Lease or facility name |
| api_no | str | 8-digit API number |
| county | str | County name |
| well_no | str | Well number |
| inspection_date | str | Date of inspection |
| drilling_permit_no | str | Drilling permit number |
| complaint_no | str | Complaint number (if complaint-driven) |
| compliance | str | Compliance status |
| field_name | str | RRC field name |
| api10 | str | Derived: "42" + api_no (10-digit) |
| scraped_at | str | Ingestion timestamp |

**Source:** }-delimited ASCII with header row. All columns preserved as str.

---

## twip_dim_drilling_permits

RRC drilling permit records. 948,729 rows. Key fields extracted by observed position from 510-byte fixed-width source.

| Column | Type | Description |
|--------|------|-------------|
| district | str | RRC district code |
| permit_number | str | Permit number |
| lease_name | str | Lease name |
| district_suffix | str | District suffix code |
| total_depth | str | Total depth (ft) |
| county_code | str | County code |
| field_number | str | Field number |
| well_number | str | Well number |
| remarks | str | Permit remarks |
| operator_number | str | Operator number |
| api_county | str | API county code |
| api_unique | str | API unique well code |
| raw_line | str | First 510 chars of source line preserved |
| api10 | str | Derived: "42" + api_county + api_unique |
| scraped_at | str | Ingestion timestamp |

---

## twip_dim_hearings

RRC hearing/docket records. 5,055,787 rows. Multi-record-type source (01=header, 02=party, 15=subject, 03/04/16=other types).

| Column | Type | Description |
|--------|------|-------------|
| record_type | str | Record type code (01, 02, 15, etc.) |
| raw_line | str | First 200 chars of source line |
| line_number_in_file | int | Position in source file |
| docket_number | str | Docket number (type 01 only) |
| case_type | str | Case type code (type 01 only) |
| status_code | str | Status (type 01 only) |
| filing_date | str | Filing date (type 01 only) |
| party_name | str | Party/operator name (type 02 only) |
| operator_number | str | Operator number (type 02 only) |
| line_number | str | Line number (type 15 only) |
| subject_text | str | Subject description (type 15 only) |
| scraped_at | str | Ingestion timestamp |

---

## twip_dim_operator_consolidation

Empty stub. Populated incrementally as M&A events surface.

---

## Notes

- **api10 derivation:** api10 = "42" + apinum (Texas state code + 8-digit county+well)
- **api14 not available** from this source (no sequence/drillhole digits in the .dbf)
- **All identifier columns stored as str**, preserved verbatim from source
- **No derived "current" attributes** on master at ingestion time
