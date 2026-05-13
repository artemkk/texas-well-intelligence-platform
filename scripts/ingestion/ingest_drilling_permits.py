"""Ingest RRC drilling permits (daf804.txt.gz) into twip_dim_drilling_permits.

The source is a 510-byte fixed-width file. Without the full COBOL layout doc,
this parser extracts key fields by observed position and preserves the full
raw line for downstream refinement.

Usage:
    python scripts/ingestion/ingest_drilling_permits.py --subset 1000
    python scripts/ingestion/ingest_drilling_permits.py
"""
from __future__ import annotations
import argparse, gzip, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/drilling_permits.log")
DEFAULT_SOURCE = Path("data/sources/rrc/drilling_permits")
OUTPUT_DIR = Path("data/raw/twip_dim_drilling_permits")

# Observed field positions from sample lines (510-byte records)
# Positions are 0-indexed
LAYOUT = [
    ("district",           0,  2),
    ("permit_number",      2,  6),
    ("lease_name",         8, 32),
    ("district_suffix",   40,  4),
    ("total_depth",       48,  5),
    ("county_code",       53,  3),
    ("field_number",      56,  5),
    ("well_number",       61,  3),
    ("remarks",           64, 30),
    ("operator_number",   94,  6),
    ("api_county",       100,  3),
    ("api_unique",       103,  5),
]


def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_drilling_permits")
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
    gz = sorted(source_dir.glob("*.gz"), reverse=True)
    txt = sorted(source_dir.glob("*.txt"), reverse=True)
    return (gz + txt)[0] if (gz + txt) else None


def ingest(source_path, output_dir, subset, log):
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_dim_drilling_permits.parquet"
    tmp_path = output_dir / "twip_dim_drilling_permits.parquet.tmp"

    log.info(f"Source: {source_path} ({source_path.stat().st_size/1024/1024:.1f} MB)")

    opener = gzip.open if str(source_path).endswith(".gz") else open
    rows = []
    start = time.time()
    last_hb = start

    with opener(str(source_path), "rt", encoding="ascii", errors="replace") as f:
        for i, line in enumerate(f):
            if len(line.rstrip()) < 50:
                continue
            row = {"raw_line": line.rstrip()[:510]}
            for name, pos, length in LAYOUT:
                row[name] = line[pos:pos+length].strip()

            # Derive api10 if county + unique are present
            county = row.get("api_county", "").zfill(3)
            unique = row.get("api_unique", "").zfill(5)
            if county and unique and len(county) == 3 and len(unique) == 5:
                row["api10"] = "42" + county + unique
            else:
                row["api10"] = None

            rows.append(row)

            if subset and len(rows) >= subset:
                log.info(f"Subset limit: {subset}")
                break

            now = time.time()
            if now - last_hb >= 60:
                log.info(f"HEARTBEAT: {len(rows):,} rows parsed, {now-start:.0f}s")
                last_hb = now

    df = pd.DataFrame(rows)
    df["scraped_at"] = datetime.now(timezone.utc).isoformat()
    log.info(f"Parsed: {len(df):,} rows, {len(df.columns)} cols")

    df.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))
    log.info(f"Written: {out_path} ({len(df):,} rows, {out_path.stat().st_size/1024/1024:.1f} MB)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} permits in {time.time()-start:.1f}s")


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
        ingest(src, args.output_dir, args.subset, log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
