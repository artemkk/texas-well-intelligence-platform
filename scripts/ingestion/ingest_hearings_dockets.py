"""Ingest RRC hearings/dockets (OD_DUMP) into twip_dim_hearings.

Multi-record-type file: type 01 = docket header, type 02 = party info,
type 15 = subject/description. Extracts all record types and stores
in a single table with record_type column for downstream filtering.

Usage:
    python scripts/ingestion/ingest_hearings_dockets.py --subset 1000
    python scripts/ingestion/ingest_hearings_dockets.py
"""
from __future__ import annotations
import argparse, gzip, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/hearings_dockets.log")
DEFAULT_SOURCE = Path("data/sources/rrc/hearings_dockets")
OUTPUT_DIR = Path("data/raw/twip_dim_hearings")

# Record type 01 (docket header) observed positions
LAYOUT_01 = [
    ("record_type",    0,  2),
    ("docket_number",  7,  5),
    ("case_type",     12,  3),
    ("status_code",   15,  1),
    ("filing_date",   80,  8),  # Approximate — YYYYMMDD
]

# Record type 02 (party/operator)
LAYOUT_02 = [
    ("record_type",    0,  2),
    ("party_name",     2, 40),
    ("operator_number", 42, 6),
]

# Record type 15 (subject/description)
LAYOUT_15 = [
    ("record_type",    0,  2),
    ("line_number",    2,  4),
    ("subject_text",   6, 50),
]


def setup_logging(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_hearings")
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
    out_path = output_dir / "twip_dim_hearings.parquet"
    tmp_path = output_dir / "twip_dim_hearings.parquet.tmp"

    log.info(f"Source: {source_path} ({source_path.stat().st_size/1024/1024:.1f} MB)")

    opener = gzip.open if str(source_path).endswith(".gz") else open
    rows = []
    rec_type_counts = {}
    start = time.time()
    last_hb = start

    with opener(str(source_path), "rt", encoding="ascii", errors="replace") as f:
        for i, line in enumerate(f):
            if len(line.rstrip()) < 2:
                continue
            rec_type = line[:2].strip()
            rec_type_counts[rec_type] = rec_type_counts.get(rec_type, 0) + 1

            row = {
                "record_type": rec_type,
                "raw_line": line.rstrip()[:200],  # First 200 chars for reference
                "line_number_in_file": i,
            }

            if rec_type == "01":
                for name, pos, length in LAYOUT_01:
                    if name != "record_type":
                        row[name] = line[pos:pos+length].strip()
            elif rec_type == "02":
                for name, pos, length in LAYOUT_02:
                    if name != "record_type":
                        row[name] = line[pos:pos+length].strip()
            elif rec_type == "15":
                for name, pos, length in LAYOUT_15:
                    if name != "record_type":
                        row[name] = line[pos:pos+length].strip()

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
    log.info(f"Record type distribution: {rec_type_counts}")
    log.info(f"Parsed: {len(df):,} rows")

    df.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))
    log.info(f"Written: {out_path} ({len(df):,} rows, {out_path.stat().st_size/1024/1024:.1f} MB)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} hearing records in {time.time()-start:.1f}s")


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
