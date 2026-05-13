"""Build well-lease crosswalk from twip_fact_well_completions.

Maps api10 to lease_name with effective date ranges, enabling
lease-level production data to join to the well-level backbone.

Usage:
    python scripts/ingestion/build_well_lease_crosswalk.py
    python scripts/ingestion/build_well_lease_crosswalk.py --subset 100
"""
from __future__ import annotations
import argparse, logging, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

LOG_PATH = Path("logs/well_lease_crosswalk.log")
COMP_PATH = Path("data/raw/twip_fact_well_completions/twip_fact_well_completions.parquet")
OUTPUT_DIR = Path("data/raw/twip_dim_well_lease_crosswalk")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("well_lease_crosswalk")
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


def build(subset: int | None, log: logging.Logger):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "twip_dim_well_lease_crosswalk.parquet"
    tmp_path = OUTPUT_DIR / "twip_dim_well_lease_crosswalk.parquet.tmp"

    comp = pd.read_parquet(COMP_PATH)
    log.info(f"Completions loaded: {len(comp):,} rows")

    if subset:
        apis = comp["api10"].unique()[:subset]
        comp = comp[comp["api10"].isin(apis)]
        log.info(f"Subset: {len(apis)} api10s")

    # Filter to rows with non-null lease_name
    has_lease = comp[comp["lease_name"].notna()].copy()
    log.info(f"Rows with lease_name: {len(has_lease):,}")

    # For each (api10, lease_name) pair: first and last completion dates
    has_lease["comp_num"] = pd.to_numeric(has_lease["completion"], errors="coerce")

    grouped = has_lease.groupby(["api10", "lease_name"]).agg(
        first_completion=("comp_num", "min"),
        last_completion=("comp_num", "max"),
        n_completions=("gas_rrcid", "count"),
    ).reset_index()

    # Determine is_current: the most recent lease per api10
    most_recent = has_lease.sort_values("comp_num").groupby("api10").last()["lease_name"]
    grouped["is_current"] = grouped.apply(
        lambda r: most_recent.get(r["api10"]) == r["lease_name"], axis=1)

    # Format dates
    def fmt_date(v):
        s = str(int(v)) if pd.notna(v) and v > 0 else ""
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return None

    grouped["effective_date"] = grouped["first_completion"].apply(fmt_date)
    grouped["termination_date"] = grouped.apply(
        lambda r: None if r["is_current"] else fmt_date(r["last_completion"]), axis=1)

    # Final schema
    result = grouped[["api10", "lease_name", "effective_date", "termination_date",
                       "is_current", "n_completions"]].copy()
    result["district"] = ""  # Not derivable from completions directly
    result["scraped_at"] = datetime.now(timezone.utc).isoformat()

    log.info(f"Crosswalk: {len(result):,} (api10, lease_name) pairs")
    log.info(f"  Unique api10s: {result['api10'].nunique():,}")
    log.info(f"  Unique leases: {result['lease_name'].nunique():,}")
    log.info(f"  is_current=True: {result['is_current'].sum():,}")

    # Atomic write
    result.to_parquet(str(tmp_path), index=False)
    os.replace(str(tmp_path), str(out_path))

    log.info(f"Written: {out_path} ({len(result):,} rows)")
    log.info(f"PIPELINE_COMPLETE: {len(result):,} crosswalk rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", type=int, default=None)
    args = ap.parse_args()
    log = setup_logging(LOG_PATH)
    try:
        build(args.subset, log)
    except Exception as e:
        log.error(f"PIPELINE_FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
