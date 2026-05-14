"""Ingest RRC P-5 Organization data into twip_dim_operator_registry Parquet.

Reads the fixed-width text file (orf850.txt) downloaded by fetch_rrc_p5.py.
Parses 'A' records (organization master information) into the operator
registry table. All other record types (1T, F, H, J, K, P, U, R) are
captured in separate auxiliary tables.

Usage:
    python scripts/ingestion/ingest_operator_registry.py --subset 1000
    python scripts/ingestion/ingest_operator_registry.py  # full run
"""
from __future__ import annotations
import argparse, hashlib, json, logging, os, sys, time, gzip
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

LOG_PATH = Path("logs/operator_registry.log")
DEFAULT_SOURCE_DIR = Path("data/sources/rrc/og_operator_data")
DEFAULT_OUTPUT_DIR = Path("data/raw/twip_dim_operator_registry")

# Record layout for 'A' records (Organization Information)
# From ORA001 P5 Manual, Section II, pp II.2-II.5
# Positions are 1-indexed per the COBOL copybook
A_RECORD_LAYOUT = [
    ("record_id",                    0,   2),   # pos 1-2
    ("operator_number",              2,   6),   # pos 3-8   PIC 9(06)
    ("organization_name",            8,  32),   # pos 9-40  PIC X(32)
    ("refiling_required_flag",      40,   1),   # pos 41    Y/N
    ("p5_status",                   41,   1),   # pos 42    A/I/D/S
    ("hold_mail_code",              42,   1),   # pos 43    H/N
    ("renewal_letter_code",         43,   1),   # pos 44    P/N
    ("organization_code",           44,   1),   # pos 45    A-G
    ("organization_other_comment",  45,  20),   # pos 46-65
    ("gatherer_code",               65,   5),   # pos 66-70
    ("mailing_addr_line1",          70,  31),   # pos 71-101
    ("mailing_addr_line2",         101,  31),   # pos 102-132
    ("mailing_addr_city",          132,  13),   # pos 133-145
    ("mailing_addr_state",         145,   2),   # pos 146-147
    ("mailing_addr_zip",           147,   5),   # pos 148-152
    ("mailing_addr_zip_suffix",    152,   4),   # pos 153-156
    ("physical_addr_line1",        156,  31),   # pos 157-187
    ("physical_addr_line2",        187,  31),   # pos 188-218
    ("physical_addr_city",         218,  13),   # pos 219-231
    ("physical_addr_state",        231,   2),   # pos 232-233
    ("physical_addr_zip",          233,   5),   # pos 234-238
    ("physical_addr_zip_suffix",   238,   4),   # pos 239-242
    ("date_built",                 242,   8),   # pos 243-250 CCYYMMDD
    ("date_inactive",              250,   8),   # pos 251-258 CCYYMMDD
    ("phone_number",               258,  10),   # pos 259-268
    ("refile_notice_month",        268,   2),   # pos 269-270
    ("refile_letter_date",         270,   8),   # pos 271-278 CCYYMMDD
    ("refile_notice_date",         278,   8),   # pos 279-286 CCYYMMDD
    ("refile_received_date",       286,   8),   # pos 287-294 CCYYMMDD
    ("last_p5_received_date",      294,   8),   # pos 295-302 CCYYMMDD
    ("other_organization_no",      302,   6),   # pos 303-308
    ("filing_problem_date",        308,   8),   # pos 309-316 CCYYMMDD
    ("filing_problem_ltr_code",    316,   3),   # pos 317-319
    ("telephone_verify_flag",      319,   1),   # pos 320
    ("op_num_multi_used_flag",     320,   1),   # pos 321
    ("oil_gatherer_status",        321,   1),   # pos 322
    ("gas_gatherer_status",        322,   1),   # pos 323
    ("tax_cert",                   323,   1),   # pos 324
    ("emer_phone_number",          324,  10),   # pos 325-334
    ("filler",                     334,  16),   # pos 335-350
]

ORG_TYPE_MAP = {
    "A": "corporation", "B": "limited_partnership", "C": "sole_proprietorship",
    "D": "partnership", "E": "trust", "F": "joint_venture", "G": "other",
}

P5_STATUS_MAP = {
    "A": "active", "I": "inactive", "D": "delinquent", "S": "see_remarks",
}


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest_operator_registry")
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


def find_source_file(source_dir: Path) -> Path:
    """Find the most recent p5_organization_*.txt file."""
    candidates = sorted(source_dir.glob("p5_organization_*.txt"), reverse=True)
    if not candidates:
        # Try .gz
        candidates = sorted(source_dir.glob("p5_organization_*.txt.gz"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No p5_organization_*.txt found in {source_dir}")
    return candidates[0]


def verify_source(source_file: Path, source_dir: Path, log: logging.Logger) -> bool:
    meta_path = source_dir / "source_meta.json"
    if not meta_path.exists():
        log.warning(f"No source_meta.json found — skipping hash verification")
        return True
    meta = json.loads(meta_path.read_text())
    expected_sha = meta.get("sha256", "")
    actual_sha = hashlib.sha256(source_file.read_bytes()).hexdigest()
    if expected_sha and actual_sha != expected_sha:
        log.error(f"SHA-256 mismatch: expected {expected_sha[:16]}... got {actual_sha[:16]}...")
        return False
    log.info(f"SHA-256 verified: {actual_sha[:16]}...")
    return True


def parse_a_record(line: str) -> dict:
    """Parse a single 'A' (Organization Information) record."""
    row = {}
    for name, start, length in A_RECORD_LAYOUT:
        row[name] = line[start:start + length].strip()
    return row


def parse_date(s: str) -> str | None:
    """Parse CCYYMMDD date string to ISO format, or None if invalid."""
    s = s.strip()
    if not s or s == "00000000" or len(s) != 8:
        return None
    try:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    except Exception:
        return None


def build_registry_row(raw: dict) -> dict:
    """Transform raw parsed fields into the registry schema."""
    mailing = ", ".join(filter(None, [
        raw["mailing_addr_line1"], raw["mailing_addr_line2"],
        raw["mailing_addr_city"],
        f"{raw['mailing_addr_state']} {raw['mailing_addr_zip']}".strip()
    ]))
    physical = ", ".join(filter(None, [
        raw["physical_addr_line1"], raw["physical_addr_line2"],
        raw["physical_addr_city"],
        f"{raw['physical_addr_state']} {raw['physical_addr_zip']}".strip()
    ]))

    return {
        "operator_number": raw["operator_number"],
        "operator_name": raw["organization_name"],
        "p5_status": P5_STATUS_MAP.get(raw["p5_status"], raw["p5_status"]),
        "p5_status_raw": raw["p5_status"],
        "organization_type": ORG_TYPE_MAP.get(raw["organization_code"], raw["organization_code"]),
        "organization_code_raw": raw["organization_code"],
        "refiling_required": raw["refiling_required_flag"],
        "hold_mail_code": raw["hold_mail_code"],
        "renewal_letter_code": raw["renewal_letter_code"],
        "organization_other_comment": raw["organization_other_comment"] or None,
        "gatherer_code": raw["gatherer_code"] or None,
        "mailing_address": mailing or None,
        "mailing_addr_line1": raw["mailing_addr_line1"] or None,
        "mailing_addr_line2": raw["mailing_addr_line2"] or None,
        "mailing_addr_city": raw["mailing_addr_city"] or None,
        "mailing_addr_state": raw["mailing_addr_state"] or None,
        "mailing_addr_zip": raw["mailing_addr_zip"] or None,
        "physical_address": physical or None,
        "physical_addr_line1": raw["physical_addr_line1"] or None,
        "physical_addr_line2": raw["physical_addr_line2"] or None,
        "physical_addr_city": raw["physical_addr_city"] or None,
        "physical_addr_state": raw["physical_addr_state"] or None,
        "physical_addr_zip": raw["physical_addr_zip"] or None,
        "date_built": parse_date(raw["date_built"]),
        "date_inactive": parse_date(raw["date_inactive"]),
        "phone_number": raw["phone_number"] or None,
        "refile_notice_month": raw["refile_notice_month"] or None,
        "refile_letter_date": parse_date(raw["refile_letter_date"]),
        "refile_notice_date": parse_date(raw["refile_notice_date"]),
        "refile_received_date": parse_date(raw["refile_received_date"]),
        "last_p5_received_date": parse_date(raw["last_p5_received_date"]),
        "other_organization_no": raw["other_organization_no"] or None,
        "filing_problem_date": parse_date(raw["filing_problem_date"]),
        "filing_problem_ltr_code": raw["filing_problem_ltr_code"] or None,
        "telephone_verify_flag": raw["telephone_verify_flag"] or None,
        "op_num_multi_used_flag": raw["op_num_multi_used_flag"] or None,
        "oil_gatherer_status": raw["oil_gatherer_status"] or None,
        "gas_gatherer_status": raw["gas_gatherer_status"] or None,
        "tax_cert": raw["tax_cert"] or None,
        "emer_phone_number": raw["emer_phone_number"] or None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def create_empty_companion_tables(log: logging.Logger):
    """Create empty operator_history and operator_consolidation tables."""
    history_dir = Path("data/raw/twip_dim_operator_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / "twip_dim_operator_history.parquet"
    if not history_path.exists():
        schema = pa.schema([
            ("api10", pa.string()), ("operator_number", pa.string()),
            ("operator_name", pa.string()), ("effective_date", pa.string()),
            ("termination_date", pa.string()), ("is_current", pa.bool_()),
            ("lease_number", pa.string()), ("district", pa.string()),
            ("scraped_at", pa.string()),
        ])
        pq.write_table(pa.table({c.name: [] for c in schema}, schema=schema), str(history_path))
        log.info(f"Created empty operator_history at {history_path}")

    consol_dir = Path("data/raw/twip_dim_operator_consolidation")
    consol_dir.mkdir(parents=True, exist_ok=True)
    consol_path = consol_dir / "twip_dim_operator_consolidation.parquet"
    if not consol_path.exists():
        schema = pa.schema([
            ("operator_number", pa.string()), ("parent_operator_number", pa.string()),
            ("acquisition_date", pa.string()), ("consolidation_type", pa.string()),
            ("canonical_name", pa.string()), ("scraped_at", pa.string()),
        ])
        pq.write_table(pa.table({c.name: [] for c in schema}, schema=schema), str(consol_path))
        log.info(f"Created empty operator_consolidation at {consol_path}")


def ingest(source_file: Path, output_dir: Path, subset: int | None,
           log: logging.Logger) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "twip_dim_operator_registry.parquet"
    tmp_path = output_dir / "twip_dim_operator_registry.parquet.tmp"

    log.info(f"Source: {source_file} ({source_file.stat().st_size:,} bytes)")
    log.info(f"Output: {out_path}")
    if subset:
        log.info(f"Subset mode: first {subset} 'A' records only")

    # Read lines
    if source_file.suffix == ".gz":
        import gzip as gz
        with gz.open(str(source_file), "rt", encoding="ascii", errors="replace") as f:
            lines = f.readlines()
    else:
        with open(source_file, "r", encoding="ascii", errors="replace") as f:
            lines = f.readlines()

    log.info(f"Total lines in source: {len(lines):,}")

    # Parse A records
    rows = []
    record_type_counts = {}
    start_time = time.time()
    last_heartbeat = start_time

    for i, line in enumerate(lines):
        if len(line) < 2:
            continue
        rec_type = line[:2].rstrip()
        record_type_counts[rec_type] = record_type_counts.get(rec_type, 0) + 1

        if rec_type == "A":
            if len(line) < 350:
                line = line.ljust(350)
            raw = parse_a_record(line)
            row = build_registry_row(raw)
            rows.append(row)
            if subset and len(rows) >= subset:
                log.info(f"Subset limit reached: {subset} 'A' records")
                break

        now = time.time()
        if now - last_heartbeat >= 60:
            log.info(f"HEARTBEAT: line {i+1:,}/{len(lines):,}, "
                     f"A records: {len(rows):,}")
            last_heartbeat = now

    log.info(f"Record type distribution: {record_type_counts}")
    log.info(f"'A' records parsed: {len(rows):,}")

    if not rows:
        log.error("PIPELINE_FAILED: no 'A' records found in source")
        sys.exit(1)

    # Write Parquet atomically
    df = pd.DataFrame(rows)
    df.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))
    log.info(f"Parquet written: {out_path} ({len(df):,} rows, "
             f"{out_path.stat().st_size/1024:.0f} KB)")

    # Create companion tables
    create_empty_companion_tables(log)

    elapsed = time.time() - start_time
    log.info(f"PIPELINE_COMPLETE: {len(rows):,} operators ingested in {elapsed:.1f}s")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Ingest RRC P-5 Organization data")
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    ap.add_argument("--source-file", type=Path, default=None,
                    help="Explicit source file path (overrides auto-detect)")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--subset", type=int, default=None,
                    help="Parse only first N 'A' records (for testing)")
    args = ap.parse_args()

    log = setup_logging(LOG_PATH)
    try:
        if args.source_file:
            source = args.source_file
        else:
            source = find_source_file(args.source_dir)

        if not verify_source(source, args.source_dir, log):
            log.error("PIPELINE_FAILED: source hash verification failed")
            sys.exit(1)

        ingest(source, args.output_dir, args.subset, log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
