"""Ingest RRC injection/UIC data (uif700a.txt.gz) into twip_dim_injection_uic.

Fixed-width ASCII text, gzipped. Record type in first 2 chars.

Usage:
    python scripts/ingestion/ingest_injection_uic.py --subset 1000
    python scripts/ingestion/ingest_injection_uic.py
"""
from __future__ import annotations
import argparse, gzip, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/injection_uic.log")
DEFAULT_SOURCE = Path("data/sources/rrc/injection_uic")
OUTPUT_DIR = Path("data/raw/twip_dim_injection_uic")
RAW_DIR = Path("data/raw/twip_dim_injection_uic_raw")


def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_injection_uic")
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
    for ext in ["*.gz", "*.txt", "*.dat"]:
        files = sorted(source_dir.glob(ext), reverse=True)
        if files:
            return files[0]
    return None


def ingest(source_path, output_dir, raw_dir, subset, log):
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_dim_injection_uic.parquet"
    raw_path = raw_dir / "twip_dim_injection_uic_raw.parquet"

    log.info(f"Source: {source_path} ({source_path.stat().st_size/1024/1024:.1f} MB)")

    opener = gzip.open if str(source_path).endswith(".gz") else open
    rows = []
    rec_type_counts = {}
    start = time.time()
    last_hb = start

    with opener(str(source_path), "rt", encoding="ascii", errors="replace") as f:
        for i, line in enumerate(f):
            if len(line.rstrip()) < 10:
                continue
            rec_type = line[:2].strip()
            rec_type_counts[rec_type] = rec_type_counts.get(rec_type, 0) + 1

            # Parse key fields from observed positions
            row = {
                "record_type": rec_type,
                "district": line[2:4].strip(),
                "lease_number": line[4:10].strip(),
                "well_type_code": line[10:11].strip(),
                "county_code": line[11:14].strip(),
                "field_number": line[14:22].strip(),
                "operator_number": line[22:28].strip(),
                "api_county": line[28:31].strip(),
                "api_unique": line[31:36].strip(),
                "raw_line": line.rstrip()[:200],
            }

            # Derive api10
            county = row["api_county"].zfill(3)
            unique = row["api_unique"].zfill(5)
            if county != "000" and unique != "00000":
                row["api10"] = "42" + county + unique
            else:
                row["api10"] = None

            rows.append(row)

            if subset and len(rows) >= subset:
                log.info(f"Subset limit: {subset}")
                break

            now = time.time()
            if now - last_hb >= 60:
                log.info(f"HEARTBEAT: {len(rows):,} rows, {now-start:.0f}s")
                last_hb = now

    df = pd.DataFrame(rows)
    df["scraped_at"] = datetime.now(timezone.utc).isoformat()
    log.info(f"Record types: {rec_type_counts}")
    log.info(f"Parsed: {len(df):,} rows")

    # Raw
    raw_tmp = raw_dir / "twip_dim_injection_uic_raw.parquet.tmp"
    df.to_parquet(str(raw_tmp), index=False)
    os.replace(str(raw_tmp), str(raw_path))
    log.info(f"Raw: {raw_path} ({len(df):,} rows)")

    # Derived (filter to type 01 = well header records if applicable)
    if "01" in rec_type_counts:
        derived = df[df["record_type"] == "01"].copy()
    else:
        derived = df.copy()

    tmp = output_dir / "twip_dim_injection_uic.parquet.tmp"
    derived.to_parquet(str(tmp), index=False)
    os.replace(str(tmp), str(out_path))

    elapsed = time.time() - start
    log.info(f"Derived: {out_path} ({len(derived):,} rows)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} total rows, {len(derived):,} derived in {elapsed:.1f}s")


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
