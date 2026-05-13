"""Ingest RRC Oil Production Data (EBCDIC + COMP-3) into twip_fact_production_monthly.

Source: PDF100.ebc (OIL TAPE), EBCDIC character set, 102-byte fixed records.
Layout: PDA001 COBOL copybook (49 pages).

Record types: 01=Root, 02=Reporting Cycle, 03=Production, 04=Discrepancy,
05=Disposition, 06=Casinghead Disposition, 07=Previous Production Report,
08-13=Commingle segments, 22=Remarks, 23=Disposition Remarks, 24=Commingle Remarks.

Hierarchy: Root(01) → Reporting Cycle(02) → Production(03) + Disposition(05) + ...

Usage:
    python scripts/ingestion/ingest_production_data.py --subset 10000
    python scripts/ingestion/ingest_production_data.py
"""
from __future__ import annotations
import argparse, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/production_data.log")
DEFAULT_SOURCE = Path("data/sources/rrc/production_data")
OUTPUT_DIR = Path("data/raw/twip_fact_production_monthly")
RAW_DIR = Path("data/raw/twip_fact_production_records_raw")

RECORD_LENGTH = 102


def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_production")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                       datefmt="%Y-%m-%dT%H:%M:%S"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                       datefmt="%H:%M:%S"))
    logger.addHandler(sh)
    return logger


def find_source(source_dir):
    for ext in ["*.txt", "*.ebc", "*.dat"]:
        files = sorted(source_dir.glob(ext), reverse=True)
        if files:
            return files[0]
    return None


def decode_ebcdic(raw: bytes) -> str:
    """Decode EBCDIC bytes to ASCII string."""
    return raw.decode("cp037", errors="replace")


def unpack_comp3(raw: bytes) -> int:
    """Unpack COMP-3 (packed decimal) bytes to integer.
    PIC S9(09) COMP-3 = 5 bytes = 9 digits + sign nibble.
    High nibble of each byte = digit, low nibble = digit (except last byte).
    Last byte: high nibble = digit, low nibble = sign (C=positive, D=negative, F=unsigned positive).
    """
    if not raw or len(raw) == 0:
        return 0
    result = 0
    for byte in raw[:-1]:
        hi = (byte >> 4) & 0x0F
        lo = byte & 0x0F
        result = result * 100 + hi * 10 + lo
    # Last byte
    last = raw[-1]
    hi = (last >> 4) & 0x0F
    sign = last & 0x0F
    result = result * 10 + hi
    if sign == 0x0D or sign == 0x0B:  # negative
        result = -result
    return result


def parse_root_01(rec: bytes) -> dict:
    """Parse Root Segment (01). Record length 50 bytes data + 52 filler."""
    return {
        "record_type": "01",
        "oil_code": decode_ebcdic(rec[2:3]),           # pos 3, PIC X(1)
        "district": decode_ebcdic(rec[3:5]),            # pos 4, PIC 9(2)
        "lease_number": decode_ebcdic(rec[5:11]),       # pos 6, PIC 9(06)
        "movable_balance": unpack_comp3(rec[11:16]),    # pos 12, COMP-3 5 bytes
        "beginning_oil_status": unpack_comp3(rec[16:21]),  # pos 17
        "beginning_csghd_status": unpack_comp3(rec[21:26]),  # pos 22
        "oil_oldest_eom_balance": unpack_comp3(rec[26:31]),  # pos 27
    }


def parse_reporting_cycle_02(rec: bytes) -> dict:
    """Parse Reporting Cycle Segment (02). Record length 80 bytes data + 22 filler."""
    return {
        "record_type": "02",
        "rpt_cycle_key": decode_ebcdic(rec[2:6]),       # pos 3, PIC 9(04) = MMYY
        "daily_oil_prorated_allow": unpack_comp3(rec[6:11]),  # pos 7
        "daily_oil_exempt_allow": unpack_comp3(rec[11:16]),   # pos 12
        "daily_csh_prorated_allow": unpack_comp3(rec[16:21]), # pos 17
        "daily_csh_exempt_allow": unpack_comp3(rec[21:26]),   # pos 22
        "oil_allowable_cycle_bbls": unpack_comp3(rec[26:31]), # pos 27
        "csh_limit_cycle_mcf": unpack_comp3(rec[31:36]),      # pos 32
        "oil_allow_effect_year": decode_ebcdic(rec[36:40]),   # pos 37
        "oil_allow_effect_month": decode_ebcdic(rec[40:42]),  # pos 41
        "oil_allow_effect_day": decode_ebcdic(rec[42:44]),    # pos 43
        "oil_allow_issue_year": decode_ebcdic(rec[44:48]),    # pos 45
        "oil_allow_issue_month": decode_ebcdic(rec[48:50]),   # pos 49
        "oil_allow_issue_day": decode_ebcdic(rec[50:52]),     # pos 51
        "oil_ending_balance": unpack_comp3(rec[52:57]),       # pos 53
        "present_oil_status": unpack_comp3(rec[57:62]),       # pos 58
        "present_csghd_status": unpack_comp3(rec[62:67]),     # pos 63
        "adjusted_oil_status": unpack_comp3(rec[67:72]),      # pos 68
        "adjusted_csghd_status": unpack_comp3(rec[72:77]),    # pos 73
    }


def parse_production_03(rec: bytes) -> dict:
    """Parse Production Segment (03). Record length 38 bytes data + 64 filler.
    THIS IS THE KEY SEGMENT — contains actual production volumes."""
    return {
        "record_type": "03",
        "corrected_report_flag": decode_ebcdic(rec[2:3]),     # pos 3, N/Y
        "oil_production_bbl": unpack_comp3(rec[6:11]),        # pos 7, COMP-3
        "casinghead_gas_mcf": unpack_comp3(rec[11:16]),       # pos 12, COMP-3
        "casinghead_gas_lift": unpack_comp3(rec[16:21]),      # pos 17, COMP-3
        "batch_number": decode_ebcdic(rec[21:24]),            # pos 22
        "item_number": decode_ebcdic(rec[24:28]),             # pos 25
        "posting_year": decode_ebcdic(rec[28:32]),            # pos 29
        "posting_month": decode_ebcdic(rec[32:34]),           # pos 33
        "posting_day": decode_ebcdic(rec[34:36]),             # pos 35
        "filed_by_edi": decode_ebcdic(rec[36:37]),            # pos 37
    }


def parse_disposition_05(rec: bytes) -> dict:
    """Parse Disposition & Stock Adjustment (05). Record length 7 bytes + 95 filler."""
    return {
        "record_type": "05",
        "disposition_code": decode_ebcdic(rec[2:4]),          # pos 3, PIC 9(02)
        "disposition_amount": unpack_comp3(rec[4:9]),         # pos 5, COMP-3
    }


def ingest(source_path, output_dir, raw_dir, subset, log):
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_fact_production_monthly.parquet"
    raw_path = raw_dir / "twip_fact_production_records_raw.parquet"

    log.info(f"Source: {source_path} ({source_path.stat().st_size/1024/1024:.1f} MB)")
    log.info(f"Record length: {RECORD_LENGTH}")

    with open(source_path, "rb") as f:
        raw_data = f.read()

    file_size = len(raw_data)
    n_records = file_size // RECORD_LENGTH
    remainder = file_size % RECORD_LENGTH
    log.info(f"File: {file_size:,} bytes, {n_records:,} records, remainder {remainder}")

    if subset:
        n_records = min(n_records, subset)
        log.info(f"Subset: {n_records:,} records")

    # Parse all records, tracking hierarchy
    raw_rows = []
    production_rows = []
    current_root = {}
    current_cycle = {}
    rec_type_counts = {}
    start = time.time()
    last_hb = start

    for i in range(n_records):
        offset = i * RECORD_LENGTH
        rec = raw_data[offset:offset + RECORD_LENGTH]
        rec_id = decode_ebcdic(rec[0:2]).strip()
        rec_type_counts[rec_id] = rec_type_counts.get(rec_id, 0) + 1

        if rec_id == "01":
            current_root = parse_root_01(rec)
        elif rec_id == "02":
            current_cycle = parse_reporting_cycle_02(rec)
        elif rec_id == "03":
            prod = parse_production_03(rec)
            # Combine with parent context
            row = {
                "district": current_root.get("district", ""),
                "lease_number": current_root.get("lease_number", ""),
                "oil_code": current_root.get("oil_code", ""),
                "rpt_cycle_key": current_cycle.get("rpt_cycle_key", ""),
                "oil_production_bbl": prod["oil_production_bbl"],
                "casinghead_gas_mcf": prod["casinghead_gas_mcf"],
                "casinghead_gas_lift": prod["casinghead_gas_lift"],
                "corrected_report_flag": prod["corrected_report_flag"],
                "posting_year": prod["posting_year"],
                "posting_month": prod["posting_month"],
                "posting_day": prod["posting_day"],
                "filed_by_edi": prod["filed_by_edi"],
                "oil_ending_balance": current_cycle.get("oil_ending_balance", 0),
                "oil_allowable_cycle_bbls": current_cycle.get("oil_allowable_cycle_bbls", 0),
            }
            production_rows.append(row)

        # Raw preservation — store record type + hex for all records
        raw_rows.append({
            "record_index": i,
            "record_type": rec_id,
            "raw_hex": rec[:40].hex(),
            "district": current_root.get("district", ""),
            "lease_number": current_root.get("lease_number", ""),
        })

        now = time.time()
        if now - last_hb >= 60:
            elapsed = now - start
            rate = (i + 1) / elapsed
            log.info(f"HEARTBEAT: {i+1:,}/{n_records:,} records "
                     f"({rate:.0f} rec/s, {len(production_rows):,} production rows)")
            last_hb = now

    log.info(f"Record type distribution: {rec_type_counts}")
    log.info(f"Production rows (type 03): {len(production_rows):,}")
    log.info(f"Raw rows (all types): {len(raw_rows):,}")

    # Parse rpt_cycle_key (MMYY) into prod_month and prod_year
    df_prod = pd.DataFrame(production_rows)
    if len(df_prod) > 0:
        # rpt_cycle_key is documented as MMYY but data shows YYMM pattern
        # (values like 2304 = year 2023, month 04). Detect and handle both.
        first2 = df_prod["rpt_cycle_key"].str[:2]
        if (first2.astype(int, errors="ignore") > 12).mean() > 0.5:
            # YYMM format (most values have year > 12 in first 2 digits)
            df_prod["prod_year"] = df_prod["rpt_cycle_key"].str[:2].apply(
                lambda x: "20" + x if x < "50" else "19" + x)
            df_prod["prod_month"] = df_prod["rpt_cycle_key"].str[2:4]
        else:
            # MMYY format (as documented)
            df_prod["prod_month"] = df_prod["rpt_cycle_key"].str[:2]
            df_prod["prod_year"] = df_prod["rpt_cycle_key"].str[2:4].apply(
                lambda x: "20" + x if x < "50" else "19" + x)
        df_prod["scraped_at"] = datetime.now(timezone.utc).isoformat()

    # Write production
    tmp = output_dir / "twip_fact_production_monthly.parquet.tmp"
    df_prod.to_parquet(str(tmp), index=False)
    os.replace(str(tmp), str(out_path))
    log.info(f"Production: {out_path} ({len(df_prod):,} rows, {out_path.stat().st_size/1024/1024:.1f} MB)")

    # Write raw
    df_raw = pd.DataFrame(raw_rows)
    df_raw["scraped_at"] = datetime.now(timezone.utc).isoformat()
    raw_tmp = raw_dir / "twip_fact_production_records_raw.parquet.tmp"
    df_raw.to_parquet(str(raw_tmp), index=False)
    os.replace(str(raw_tmp), str(raw_path))
    log.info(f"Raw: {raw_path} ({len(df_raw):,} rows)")

    elapsed = time.time() - start
    log.info(f"PIPELINE_COMPLETE: {len(df_prod):,} production rows, "
             f"{len(df_raw):,} raw rows in {elapsed:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--source-path", type=Path, default=None)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    ap.add_argument("--subset", type=int, default=None)
    args = ap.parse_args()
    log = setup_logging(LOG_PATH)
    try:
        src = args.source_path or find_source(args.source_dir)
        if not src:
            log.error("PIPELINE_FAILED: no source file found")
            sys.exit(1)
        ingest(src, args.output_dir, RAW_DIR, args.subset, log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
