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

    # Add api10 (Texas API = state code 42 + county + well)
    # The dbf files may already have an API field — detect it
    api_candidates = [c for c in df.columns if "api" in c.lower()]
    log.info(f"API column candidates: {api_candidates}")

    # Add metadata
    df["scraped_at"] = datetime.now(timezone.utc).isoformat()

    # Atomic write
    df.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))

    sz = out_path.stat().st_size
    elapsed = time.time() - start
    log.info(f"Parquet written: {out_path} ({len(df):,} rows, {sz/1024/1024:.1f} MB)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} wells ingested in {elapsed:.1f}s")
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
