"""Ingest RRC production data (EBCDIC format) into twip_fact_production_monthly.

The source file (PDF100.ebc) is EBCDIC-encoded with packed decimal fields.
Converts EBCDIC to ASCII, parses fixed-width fields, outputs lease-level
monthly production.

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

# EBCDIC to ASCII translation table (IBM cp037)
EBCDIC_TABLE = bytes(range(256))
try:
    # Build translation: EBCDIC byte -> ASCII char
    _e2a = {}
    for i in range(256):
        try:
            ch = bytes([i]).decode("cp037")
            _e2a[i] = ord(ch) if len(ch) == 1 and ord(ch) < 128 else ord(" ")
        except (UnicodeDecodeError, ValueError):
            _e2a[i] = ord(" ")
    EBCDIC_TO_ASCII = bytes(_e2a[i] for i in range(256))
except Exception:
    EBCDIC_TO_ASCII = None


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
    for ext in ["*.txt", "*.ebc", "*.dat", "*.gz"]:
        files = sorted(source_dir.glob(ext), reverse=True)
        if files:
            return files[0]
    return None


def decode_packed_decimal(raw_bytes: bytes) -> float:
    """Decode IBM packed decimal (COMP-3) to float."""
    if not raw_bytes or all(b == 0 for b in raw_bytes):
        return 0.0
    result = 0
    for byte in raw_bytes[:-1]:
        hi = (byte >> 4) & 0x0F
        lo = byte & 0x0F
        result = result * 100 + hi * 10 + lo
    # Last byte: high nibble is digit, low nibble is sign
    last = raw_bytes[-1]
    hi = (last >> 4) & 0x0F
    sign_nibble = last & 0x0F
    result = result * 10 + hi
    if sign_nibble in (0x0D, 0x0B):  # negative
        result = -result
    return float(result)


def ingest(source_path, output_dir, raw_dir, subset, log):
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_fact_production_monthly.parquet"
    raw_path = raw_dir / "twip_fact_production_records_raw.parquet"

    log.info(f"Source: {source_path} ({source_path.stat().st_size/1024/1024:.1f} MB)")

    # Read the entire file as binary
    log.info("Reading EBCDIC file...")
    with open(source_path, "rb") as f:
        raw_data = f.read()

    file_size = len(raw_data)
    log.info(f"File size: {file_size:,} bytes")

    # Determine record length by finding consistent line breaks
    # EBCDIC files may not have newlines — try fixed record length
    # The RRC production file typically uses 100-byte or 200-byte records
    # Try to detect from the data pattern

    # Convert EBCDIC to ASCII for the first chunk to detect structure
    if EBCDIC_TO_ASCII:
        sample = raw_data[:2000].translate(EBCDIC_TO_ASCII).decode("ascii", errors="replace")
        log.info(f"First 200 chars (EBCDIC→ASCII): {sample[:200]}")
    else:
        sample = raw_data[:2000].decode("cp037", errors="replace")
        log.info(f"First 200 chars (cp037): {sample[:200]}")

    # Try to find record boundaries
    # Look for repeating patterns in the first few KB
    # Common RRC production record lengths: 100, 132, 156, 200
    candidate_lengths = [100, 132, 156, 180, 200, 250, 300]
    best_len = None

    for rl in candidate_lengths:
        if file_size % rl == 0 or file_size % rl < 10:
            # Check if records at this length show consistent structure
            if EBCDIC_TO_ASCII:
                r1 = raw_data[0:rl].translate(EBCDIC_TO_ASCII).decode("ascii", errors="replace")
                r2 = raw_data[rl:2*rl].translate(EBCDIC_TO_ASCII).decode("ascii", errors="replace")
            else:
                r1 = raw_data[0:rl].decode("cp037", errors="replace")
                r2 = raw_data[rl:2*rl].decode("cp037", errors="replace")
            # Check if first 2 chars look like district codes
            if r1[:2].strip().isdigit() and r2[:2].strip().isdigit():
                best_len = rl
                log.info(f"  Record length {rl}: looks good (r1={r1[:20]!r}, r2={r2[:20]!r})")
                break
            else:
                log.debug(f"  Record length {rl}: r1={r1[:20]!r}, r2={r2[:20]!r}")

    if not best_len:
        # Fallback: try newline-delimited
        if b"\n" in raw_data[:10000]:
            log.info("File appears newline-delimited")
            if EBCDIC_TO_ASCII:
                text = raw_data.translate(EBCDIC_TO_ASCII).decode("ascii", errors="replace")
            else:
                text = raw_data.decode("cp037", errors="replace")
            lines = text.split("\n")
            log.info(f"Lines: {len(lines):,}")
            best_len = None  # Use line-by-line
        else:
            log.error("PIPELINE_FAILED: cannot determine record length")
            sys.exit(1)

    start = time.time()
    rows = []
    last_hb = start

    if best_len:
        n_records = file_size // best_len
        log.info(f"Record length: {best_len}, estimated records: {n_records:,}")

        for i in range(n_records):
            if subset and len(rows) >= subset:
                break

            offset = i * best_len
            rec_raw = raw_data[offset:offset + best_len]
            if EBCDIC_TO_ASCII:
                rec = rec_raw.translate(EBCDIC_TO_ASCII).decode("ascii", errors="replace")
            else:
                rec = rec_raw.decode("cp037", errors="replace")

            row = {
                "record_raw": rec.rstrip(),
                "district": rec[0:2].strip(),
                "lease_number": rec[2:8].strip(),
            }

            # Try to extract more fields by position
            # Exact positions depend on the COBOL layout which we don't have
            # Capture what we can from visible patterns
            if len(rec) >= 40:
                row["field1"] = rec[8:14].strip()
                row["field2"] = rec[14:20].strip()
                row["field3"] = rec[20:28].strip()
                row["field4"] = rec[28:36].strip()
                row["field5"] = rec[36:44].strip()

            rows.append(row)

            now = time.time()
            if now - last_hb >= 60:
                log.info(f"HEARTBEAT: {len(rows):,}/{n_records:,} records, {now-start:.0f}s")
                last_hb = now
    else:
        # Line-by-line
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            if subset and len(rows) >= subset:
                break
            row = {
                "record_raw": line.rstrip()[:300],
                "district": line[0:2].strip() if len(line) >= 2 else "",
                "lease_number": line[2:8].strip() if len(line) >= 8 else "",
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    df["scraped_at"] = datetime.now(timezone.utc).isoformat()
    log.info(f"Parsed: {len(df):,} rows")

    # Raw preservation
    raw_tmp = raw_dir / "twip_fact_production_records_raw.parquet.tmp"
    df.to_parquet(str(raw_tmp), index=False)
    os.replace(str(raw_tmp), str(raw_path))
    log.info(f"Raw: {raw_path} ({len(df):,} rows)")

    # Derived (same structure for now — proper field extraction
    # requires the COBOL layout doc PDA001.pdf)
    tmp = output_dir / "twip_fact_production_monthly.parquet.tmp"
    df.to_parquet(str(tmp), index=False)
    os.replace(str(tmp), str(out_path))

    elapsed = time.time() - start
    log.info(f"Written: {out_path} ({len(df):,} rows, {out_path.stat().st_size/1024/1024:.1f} MB)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} production records in {elapsed:.1f}s")


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
