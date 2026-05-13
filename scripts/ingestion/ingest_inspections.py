"""Ingest RRC inspections data (}-delimited text) into twip_fact_inspections.

The source file uses } as a field delimiter with a header row.
This is the simplest of the three Phase 1 remaining sources.

Usage:
    python scripts/ingestion/ingest_inspections.py --subset 1000
    python scripts/ingestion/ingest_inspections.py
"""
from __future__ import annotations
import argparse, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/inspections.log")
DEFAULT_SOURCE = Path("data/sources/rrc/inspections")
OUTPUT_DIR = Path("data/raw/twip_fact_inspections")
RAW_DIR = Path("data/raw/twip_fact_inspections_raw")


def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_inspections")
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
    for ext in ["*.txt", "*.csv", "*.dat", "*.gz"]:
        files = sorted(source_dir.glob(ext), reverse=True)
        if files:
            return files[0]
    return None


def ingest(source_path, output_dir, raw_dir, subset, log):
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_fact_inspections.parquet"
    raw_path = raw_dir / "twip_fact_inspections_raw.parquet"
    tmp_path = output_dir / "twip_fact_inspections.parquet.tmp"
    raw_tmp = raw_dir / "twip_fact_inspections_raw.parquet.tmp"

    log.info(f"Source: {source_path} ({source_path.stat().st_size/1024/1024:.1f} MB)")

    start = time.time()

    # Read }-delimited file with header
    log.info("Reading }-delimited file...")
    df = pd.read_csv(str(source_path), sep="}", encoding="ascii",
                     encoding_errors="replace", dtype=str,
                     on_bad_lines="skip", nrows=subset)

    log.info(f"Parsed: {len(df):,} rows, {len(df.columns)} cols")
    log.info(f"Columns: {df.columns.tolist()}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Add api10 if api_no column exists
    api_cols = [c for c in df.columns if "api" in c.lower()]
    log.info(f"API column candidates: {api_cols}")
    if "api_no" in df.columns:
        df["api10"] = df["api_no"].apply(
            lambda x: "42" + str(x).strip().zfill(8) if pd.notna(x) and str(x).strip() else None)

    df["scraped_at"] = datetime.now(timezone.utc).isoformat()

    # Raw preservation
    df.to_parquet(str(raw_tmp), index=False)
    os.replace(str(raw_tmp), str(raw_path))
    log.info(f"Raw: {raw_path} ({len(df):,} rows)")

    # Derived (same as raw for inspections — no multi-record-type split needed)
    df.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))

    elapsed = time.time() - start
    log.info(f"Written: {out_path} ({len(df):,} rows, {out_path.stat().st_size/1024/1024:.1f} MB)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} inspections in {elapsed:.1f}s")


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
