"""Derive operator history from twip_fact_well_completions.

For each api10, orders completions by date and extracts operator
tenure transitions. Populates twip_dim_operator_history.

Usage:
    python scripts/ingestion/derive_operator_history.py
    python scripts/ingestion/derive_operator_history.py --subset 100
"""
from __future__ import annotations
import argparse, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/operator_history.log")
COMP_PATH = Path("data/raw/twip_fact_well_completions/twip_fact_well_completions.parquet")
OUTPUT_DIR = Path("data/raw/twip_dim_operator_history")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("derive_operator_history")
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


def derive(subset: int | None, log: logging.Logger):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "twip_dim_operator_history.parquet"
    tmp_path = OUTPUT_DIR / "twip_dim_operator_history.parquet.tmp"

    comp = pd.read_parquet(COMP_PATH)
    log.info(f"Completions loaded: {len(comp):,} rows, {comp['api10'].nunique():,} api10s")

    if subset:
        apis = comp["api10"].unique()[:subset]
        comp = comp[comp["api10"].isin(apis)]
        log.info(f"Subset: {len(apis)} api10s, {len(comp):,} rows")

    # Sort by api10 and completion date
    comp["comp_sort"] = pd.to_numeric(comp["completion"], errors="coerce").fillna(0)
    comp = comp.sort_values(["api10", "comp_sort"])

    rows = []
    start = time.time()
    last_hb = start
    api10s = comp["api10"].unique()

    for i, api in enumerate(api10s):
        well = comp[comp["api10"] == api]
        # Get ordered operator sequence (skip nulls)
        ops = well[well["operator"].notna()][["operator", "completion", "lease_name"]].values.tolist()
        if not ops:
            continue

        # Build tenure periods from operator transitions
        prev_op = None
        tenure_start = None
        for op_name, comp_date, lease in ops:
            if op_name != prev_op:
                if prev_op is not None:
                    rows.append({
                        "api10": api,
                        "operator_number": "",  # Not available in completions
                        "operator_name": prev_op,
                        "effective_date": tenure_start,
                        "termination_date": comp_date,
                        "is_current": False,
                        "lease_number": prev_lease or "",
                        "district": "",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    })
                prev_op = op_name
                tenure_start = comp_date
                prev_lease = lease

        # Last (current) operator
        if prev_op is not None:
            rows.append({
                "api10": api,
                "operator_number": "",
                "operator_name": prev_op,
                "effective_date": tenure_start,
                "termination_date": None,
                "is_current": True,
                "lease_number": prev_lease or "",
                "district": "",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        now = time.time()
        if now - last_hb >= 60:
            log.info(f"HEARTBEAT: {i+1:,}/{len(api10s):,} api10s processed, "
                     f"{len(rows):,} tenure rows")
            last_hb = now

    df = pd.DataFrame(rows)
    log.info(f"Operator history: {len(df):,} tenure rows from {len(api10s):,} api10s")

    # Verify: exactly one is_current per api10
    current_per_api = df[df["is_current"]].groupby("api10").size()
    multi_current = (current_per_api > 1).sum()
    if multi_current > 0:
        log.warning(f"{multi_current} api10s have multiple is_current=True")

    # Atomic write
    df.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))

    elapsed = time.time() - start
    log.info(f"Written: {out_path} ({len(df):,} rows)")
    log.info(f"PIPELINE_COMPLETE: {len(df):,} tenure rows in {elapsed:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", type=int, default=None)
    args = ap.parse_args()
    log = setup_logging(LOG_PATH)
    try:
        derive(args.subset, log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
