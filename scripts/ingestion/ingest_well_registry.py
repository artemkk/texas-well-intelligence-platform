"""Ingest RRC Statewide API Data (.dbf files) into twip_well_master Parquet.

Reads all county-level .dbf files downloaded by fetch_well_registry.py,
concatenates into a single statewide well_master table.

Usage:
    python scripts/ingestion/ingest_well_registry.py --subset 1000
    python scripts/ingestion/ingest_well_registry.py  # full run
"""
from __future__ import annotations
import argparse, hashlib, json, logging, os, sys, time, struct
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

LOG_PATH = Path("logs/well_registry.log")
DEFAULT_SOURCE_DIR = Path("data/sources/rrc/well_registry/dbf_files")
DEFAULT_OUTPUT_DIR = Path("data/raw/twip_well_master")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_well_registry")
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


def read_dbf_simple(path: Path) -> pd.DataFrame:
    """Read a .dbf file into a DataFrame using struct-based parsing.

    Avoids dependency on dbfread/simpledbf by parsing the dBase III format
    directly. Fields are read as bytes and decoded to strings.
    """
    with open(path, "rb") as f:
        # Header
        version = struct.unpack("B", f.read(1))[0]
        yy, mm, dd = struct.unpack("3B", f.read(3))
        num_records = struct.unpack("<I", f.read(4))[0]
        header_size = struct.unpack("<H", f.read(2))[0]
        record_size = struct.unpack("<H", f.read(2))[0]
        f.read(20)  # reserved bytes

        # Field descriptors (32 bytes each, terminated by 0x0D)
        fields = []
        while True:
            field_data = f.read(32)
            if field_data[0] == 0x0D or len(field_data) < 32:
                break
            name = field_data[:11].split(b"\x00")[0].decode("ascii").strip()
            ftype = chr(field_data[11])
            flen = field_data[16]
            fdec = field_data[17]
            fields.append((name, ftype, flen, fdec))

        # Skip to data start
        f.seek(header_size)

        # Read records
        rows = []
        for _ in range(num_records):
            record = f.read(record_size)
            if len(record) < record_size:
                break
            if record[0:1] == b"*":  # deleted record
                continue
            row = {}
            pos = 1  # skip deletion flag byte
            for name, ftype, flen, fdec in fields:
                raw = record[pos:pos + flen]
                try:
                    val = raw.decode("latin-1").strip()
                except Exception:
                    val = ""
                row[name] = val if val else None
                pos += flen
            rows.append(row)

    return pd.DataFrame(rows)


def ingest(source_dir: Path, output_dir: Path, subset: int | None,
           log: logging.Logger) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_well_master.parquet"
    tmp_path = output_dir / "twip_well_master.parquet.tmp"

    dbf_files = sorted(source_dir.glob("api*.dbf"))
    log.info(f"Found {len(dbf_files)} .dbf files in {source_dir}")

    if not dbf_files:
        log.error("PIPELINE_FAILED: no .dbf files found")
        sys.exit(1)

    all_dfs = []
    total_rows = 0
    start = time.time()
    last_heartbeat = start

    for i, dbf_path in enumerate(dbf_files):
        try:
            df = read_dbf_simple(dbf_path)
            df["source_file"] = dbf_path.name
            all_dfs.append(df)
            total_rows += len(df)

            if subset and total_rows >= subset:
                log.info(f"Subset limit reached: {total_rows} rows")
                break
        except Exception as e:
            log.warning(f"  Error reading {dbf_path.name}: {e}")

        now = time.time()
        if now - last_heartbeat >= 60:
            log.info(f"HEARTBEAT: {i+1}/{len(dbf_files)} files, "
                     f"{total_rows:,} rows, {now - start:.0f}s elapsed")
            last_heartbeat = now

    if not all_dfs:
        log.error("PIPELINE_FAILED: no data read from any .dbf file")
        sys.exit(1)

    log.info(f"Concatenating {len(all_dfs)} DataFrames...")
    df = pd.concat(all_dfs, ignore_index=True)
    log.info(f"Total rows: {len(df):,}")
    log.info(f"Columns ({len(df.columns)}): {df.columns.tolist()}")

    if subset:
        df = df.head(subset)
        log.info(f"Subset applied: {len(df)} rows")

    # Normalize column names to snake_case
    df.columns = [c.lower().strip() for c in df.columns]

    # Add api10
    df["api10"] = "42" + df["apinum"]
    now_ts = datetime.now(timezone.utc).isoformat()
    df["scraped_at"] = now_ts

    log.info(f"api10 added. Unique api10s: {df['api10'].nunique():,}")

    # ── Column classification (P-TWIP-010/011) ──
    WELL_PROPS = ["api10", "apinum", "abstract", "block", "refer_to_a",
                  "section", "survey", "total_dept", "quadnum"]
    EVENT_PROPS = ["api10", "gas_rrcid", "operator", "lease_name", "field_name",
                   "oil_gas_co", "on_off_sch", "permit_num", "completion",
                   "plug_date", "wellid"]
    META = ["scraped_at", "source_file"]

    # ── Output 1: twip_fact_well_records_raw (zero-skip, every row) ──
    raw_dir = Path("data/raw/twip_fact_well_records_raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "twip_fact_well_records_raw.parquet"
    raw_tmp = raw_dir / "twip_fact_well_records_raw.parquet.tmp"
    df.to_parquet(str(raw_tmp), index=False)
    os.replace(str(raw_tmp), str(raw_path))
    log.info(f"Raw: {raw_path} ({len(df):,} rows, {raw_path.stat().st_size/1024/1024:.1f} MB)")

    # ── Output 2: twip_well_master (one row per api10, well properties) ──
    master_cols = [c for c in WELL_PROPS if c in df.columns] + META
    master = df[master_cols].drop_duplicates("api10", keep="first")
    assert master["api10"].is_unique, "master api10 not unique after dedup"
    master_tmp = output_dir / "twip_well_master.parquet.tmp"
    master.to_parquet(str(master_tmp), index=False)
    os.replace(str(master_tmp), str(out_path))
    log.info(f"Master: {out_path} ({len(master):,} rows, unique api10: {master['api10'].nunique():,})")

    # ── Output 3: twip_fact_well_completions (one row per api10+gas_rrcid) ──
    comp_cols = [c for c in EVENT_PROPS if c in df.columns] + META
    completions = df[comp_cols].drop_duplicates(subset=["api10", "gas_rrcid"], keep="first")
    comp_dir = Path("data/raw/twip_fact_well_completions")
    comp_dir.mkdir(parents=True, exist_ok=True)
    comp_path = comp_dir / "twip_fact_well_completions.parquet"
    comp_tmp = comp_dir / "twip_fact_well_completions.parquet.tmp"
    completions.to_parquet(str(comp_tmp), index=False)
    os.replace(str(comp_tmp), str(comp_path))
    log.info(f"Completions: {comp_path} ({len(completions):,} rows)")

    # ── Verification ──
    log.info(f"Verification:")
    log.info(f"  Raw rows: {len(df):,} (= source)")
    log.info(f"  Master rows: {len(master):,} (= unique api10s)")
    log.info(f"  Completions rows: {len(completions):,} (= unique api10+gas_rrcid)")
    master_apis = set(master["api10"])
    comp_apis = set(completions["api10"])
    log.info(f"  master api10s == completions api10s: {master_apis == comp_apis}")

    # Column classification summary
    log.info(f"Column classification:")
    log.info(f"  WELL_PROPERTY (master): {[c for c in WELL_PROPS if c in df.columns]}")
    log.info(f"  EVENT_PROPERTY (completions): {[c for c in EVENT_PROPS if c in df.columns]}")

    elapsed = time.time() - start
    log.info(f"PIPELINE_COMPLETE: {len(master):,} wells, {len(completions):,} completions in {elapsed:.1f}s")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Ingest RRC Well Registry (.dbf)")
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--subset", type=int, default=None)
    args = ap.parse_args()

    log = setup_logging(LOG_PATH)
    try:
        ingest(args.source_dir, args.output_dir, args.subset, log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
