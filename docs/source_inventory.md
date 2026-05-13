# TWIP Source Inventory

*Last updated: 2026-05-13*

---

## Phase 1 — RRC Core Regulatory Sources

### Source #1: Well Registry (Statewide API Data)
- **RRC URL:** https://mft.rrc.texas.gov/link/1eb94d66-461d-4114-93f7-b4bc04a70674
- **Format:** dBase (.dbf) files, one per county (256 files)
- **Encoding:** Native dBase (Latin-1)
- **Refresh:** Twice weekly
- **Layout doc:** https://www.rrc.texas.gov/media/bkyl5qvx/well-api-manual.pdf
- **Fetcher:** scripts/automation/fetch_well_registry.py
- **Ingestion:** scripts/ingestion/ingest_well_registry.py
- **Output tables:** twip_well_master (1,154,953), twip_fact_well_completions (1,400,904), twip_fact_well_records_raw (1,500,708)
- **Status:** COMPLETE
- **Last ingestion:** 2026-05-12
- **Provenance:** data/sources/rrc/well_registry/source_meta.json

### Source #2: Production Data (Oil Tape)
- **RRC URL:** https://mft.rrc.texas.gov/link/20ff2205-6579-450f-a2ee-cbd37986b557
- **Format:** EBCDIC fixed-width, 102-byte records, COMP-3 packed decimal
- **Encoding:** IBM cp037 EBCDIC
- **Refresh:** Monthly by 27th
- **Layout doc:** PDA001 (https://www.rrc.texas.gov/media/0a4dqvag/pda001.pdf)
- **Fetcher:** scripts/automation/fetch_production_data.py
- **Ingestion:** scripts/ingestion/ingest_production_data.py
- **Output tables:** twip_fact_production_monthly (1,625,955), twip_fact_production_records_raw (10,787,639)
- **Status:** COMPLETE + VERIFIED
- **Last ingestion:** 2026-05-13
- **PDQ verification:** 10/10 PASS (2026-05-13). See docs/audits/p-twip-015-verify_pdq_verification.md
- **Notes:** 16 segment types in hierarchical structure. Only type-03 (Production) extracted to monthly table. Date format is YYMM despite PDA001 documenting MMYY.

### Source #3: Drilling Permits
- **RRC URL:** https://mft.rrc.texas.gov/link/e99fbe81-40cd-4a79-b992-9fc71d0f06d4
- **Format:** Fixed-width ASCII, gzipped (daf804.txt.gz)
- **Encoding:** ASCII
- **Refresh:** Monthly
- **Fetcher:** scripts/automation/fetch_drilling_permits.py
- **Ingestion:** scripts/ingestion/ingest_drilling_permits.py
- **Output tables:** twip_dim_drilling_permits (948,729)
- **Status:** COMPLETE
- **Last ingestion:** 2026-05-12
- **Notes:** Record layout not yet fully parsed from COBOL doc. Key fields extracted by observed position; raw_line preserved.

### Source #6: Operator Registry (P-5 Organization)
- **RRC URL:** https://mft.rrc.texas.gov/link/04652169-eed6-4396-9019-2e270e790f6c
- **Format:** Fixed-width ASCII, 350-byte records
- **Encoding:** ASCII
- **Refresh:** Monthly by 25th
- **Layout doc:** ORA001 (https://www.rrc.texas.gov/media/jtqfynn3/ora001_p5_manual_october-2014.pdf)
- **Fetcher:** scripts/automation/fetch_rrc_p5.py
- **Ingestion:** scripts/ingestion/ingest_operator_registry.py
- **Output tables:** twip_dim_operator_registry (74,947)
- **Status:** COMPLETE
- **Last ingestion:** 2026-05-12

### Source #7: Inspections & Enforcement
- **RRC URL:** https://mft.rrc.texas.gov/link/c7c28dc9-b218-4f0a-8278-bf15d009def1
- **Format:** }-delimited ASCII with header row
- **Encoding:** ASCII
- **Refresh:** Weekly on Mondays
- **Fetcher:** scripts/automation/fetch_inspections.py
- **Ingestion:** scripts/ingestion/ingest_inspections.py
- **Output tables:** twip_fact_inspections (3,867,246), twip_fact_inspections_raw (3,867,246)
- **Status:** COMPLETE
- **Last ingestion:** 2026-05-13

### Source #13: Injection/UIC Wells
- **RRC URL:** https://mft.rrc.texas.gov/link/d2438c05-b42f-45a8-b0c6-edceb0912767
- **Format:** Fixed-width ASCII, gzipped (uif700a.txt.gz)
- **Encoding:** ASCII
- **Refresh:** Monthly by 3rd workday
- **Layout doc:** https://www.rrc.texas.gov/media/v3onmigl/uic_manual_uia010_3116.pdf
- **Fetcher:** scripts/automation/fetch_injection_uic.py
- **Ingestion:** scripts/ingestion/ingest_injection_uic.py
- **Output tables:** twip_dim_injection_uic (19 type-01 records from subset), twip_dim_injection_uic_raw (1,000 from subset)
- **Status:** PARTIAL (subset only; full run pending)
- **Notes:** Target file is uif700a.txt.gz (not the README)

### Source #16: Hearings & Dockets
- **RRC URL:** https://mft.rrc.texas.gov/link/e9af053b-28c8-49b2-ad40-bf2f10f4f21a
- **Format:** Fixed-width ASCII, gzipped (OD_DUMP)
- **Encoding:** ASCII
- **Refresh:** Monthly by 27th
- **Fetcher:** scripts/automation/fetch_hearings_dockets.py
- **Ingestion:** scripts/ingestion/ingest_hearings_dockets.py
- **Output tables:** twip_dim_hearings (5,055,787)
- **Status:** COMPLETE
- **Last ingestion:** 2026-05-12

### Source #9: Bond Data (P-12)
- **Status:** NOT AVAILABLE on RRC downloads page
- **Notes:** Bond data may be embedded in P-5 operator data or require separate RRC request.

### Source #11: GIS / Shapefiles
- **RRC URL:** https://mft.rrc.texas.gov/link/d551fb20-442e-4b67-84fa-ac3f23ecabb4
- **Format:** Shapefiles (per-county ZIP archives)
- **Status:** NOT YET INGESTED (partial county download in P-TWIP-007)

### Source #14: Pipeline Permits (T-4)
- **Status:** NOT AVAILABLE on RRC downloads page

### Derived Tables (not from a single RRC source)

| Table | Source | Status | Rows |
|---|---|---|---|
| twip_dim_operator_history | Derived from twip_fact_well_completions | COMPLETE | 1,133,044 |
| twip_dim_well_lease_crosswalk | Derived from twip_fact_well_completions | COMPLETE | 1,079,625 |
| twip_dim_operator_consolidation | Empty stub, populated as M&A events surface | STUB | 0 |
