"""
TWIP QA Orchestrator — runs Level 1/2 checks for a raw table.
Per P-QA-DESIGN-001 and P-TWIP-024. Mirrors CWIP's run_qa_for_table.py.

Usage:
    python scripts/qa/run_qa_for_table.py --table-slug twip_well_master
    python scripts/qa/run_qa_for_table.py --all
"""

import argparse
import os
import sys
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.qa.check_library import (
    check_pk_unique,
    check_required_nonnull,
    check_date_range_sane,
    check_boolean_not_uniform,
    check_identifier_columns_str,
    check_schema_columns_present,
    check_row_count,
    check_fk_match_rate,
    check_cardinality_bounds,
    check_count_sanity,
)

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")

# Per-table config
TABLE_CONFIG = {
    "twip_well_master": {
        "pk": ["api10"],
        "required": ["api10", "apinum"],
        "id_cols": ["api10", "apinum"],
        "date_cols": [],
        "bool_cols": [],
        "count_range": (1000000, 1500000, "wells"),
    },
    "twip_fact_well_completions": {
        "pk": ["api10", "gas_rrcid"],
        "required": ["api10", "gas_rrcid"],
        "id_cols": ["api10"],
        "date_cols": [],
        "bool_cols": [],
        "fk": {"api10": "twip_well_master"},
    },
    "twip_fact_production_monthly": {
        "pk": None,
        "required": ["district", "lease_number", "rpt_cycle_key"],
        "id_cols": ["district", "lease_number"],
        "date_cols": [],
        "bool_cols": [],
        "count_range": (1500000, 2000000, "production rows"),
    },
    "twip_fact_inspections": {
        "pk": None,
        "required": ["api10"],
        "id_cols": ["api10"],
        "date_cols": [],
        "bool_cols": [],
        "fk": {"api10": "twip_well_master"},
    },
    "twip_dim_operator_registry": {
        "pk": ["operator_number"],
        "required": ["operator_number"],
        "id_cols": ["operator_number"],
        "date_cols": [],
        "bool_cols": [],
        "count_range": (30000, 80000, "operators"),
    },
    "twip_dim_operator_history": {
        "pk": None,
        "required": ["api10", "operator_name"],
        "id_cols": ["api10"],
        "date_cols": [],
        "bool_cols": ["is_current"],
        "fk": {"api10": "twip_well_master"},
    },
    "twip_dim_drilling_permits": {
        "pk": None,
        "required": ["api10"],
        "id_cols": ["api10"],
        "date_cols": [],
        "bool_cols": [],
        "fk": {"api10": "twip_well_master"},
    },
    "twip_dim_hearings": {
        "pk": None,
        "required": ["record_type"],
        "id_cols": [],
        "date_cols": [],
        "bool_cols": [],
    },
    "twip_dim_well_lease_crosswalk": {
        "pk": None,
        "required": ["api10", "lease_name"],
        "id_cols": ["api10"],
        "date_cols": [],
        "bool_cols": ["is_current"],
        "fk": {"api10": "twip_well_master"},
    },
}

DEFAULT_CONFIG = {
    "pk": None,
    "required": [],
    "id_cols": [],
    "date_cols": [],
    "bool_cols": [],
}


def find_table_path(slug, raw_dir=RAW_DIR):
    """Find table parquet in data/raw/{slug}/{slug}.parquet or data/raw/{slug}.parquet."""
    subdir = os.path.join(raw_dir, slug, f"{slug}.parquet")
    if os.path.exists(subdir):
        return subdir
    flat = os.path.join(raw_dir, f"{slug}.parquet")
    if os.path.exists(flat):
        return flat
    # Try without twip_ prefix for unprefixed tables
    for d in os.listdir(raw_dir):
        dp = os.path.join(raw_dir, d)
        if os.path.isdir(dp):
            fp = os.path.join(dp, f"{d}.parquet")
            if os.path.exists(fp) and d == slug:
                return fp
    return None


def get_config(slug):
    return TABLE_CONFIG.get(slug, DEFAULT_CONFIG)


def run_checks_for_table(slug, raw_dir=RAW_DIR):
    """Run all applicable checks for a single table."""
    path = find_table_path(slug, raw_dir)
    if not path:
        return [{"check_name": "table_exists", "check_level": 1,
                 "check_status": "error", "check_value": f"File not found for {slug}",
                 "check_threshold": "file exists", "notes": ""}]

    df = pd.read_parquet(path)
    config = get_config(slug)
    results = []
    now = datetime.now(timezone.utc).isoformat()
    run_id = f"retroactive-{now[:19]}"

    # Level 1 checks
    if config.get("pk"):
        results.append(check_pk_unique(df, config["pk"]))

    if config.get("required"):
        results.append(check_required_nonnull(df, config["required"]))

    if config.get("date_cols"):
        results.append(check_date_range_sane(df, config["date_cols"]))

    if config.get("bool_cols"):
        results.append(check_boolean_not_uniform(df, config["bool_cols"]))

    if config.get("id_cols"):
        results.append(check_identifier_columns_str(df, config["id_cols"]))

    # Row count (always)
    results.append(check_row_count(df, len(df), tolerance=0.0))

    # Count sanity (Level 3) if configured
    if config.get("count_range"):
        lo, hi, entity = config["count_range"]
        results.append(check_count_sanity(len(df), lo, hi, entity))

    # Add metadata
    for r in results:
        r["ingestion_run_id"] = run_id
        r["checked_at"] = now

    return results


def _qa_slug(slug):
    """Strip product prefix for QA companion naming."""
    if slug.startswith("twip_"):
        return slug[5:]
    return slug


def write_companion(slug, results, raw_dir=RAW_DIR):
    """Write QA companion table."""
    df = pd.DataFrame(results)
    cols = ["ingestion_run_id", "check_name", "check_level", "check_status",
            "check_value", "check_threshold", "checked_at", "notes"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    qa_name = _qa_slug(slug)
    out_dir = os.path.join(raw_dir, f"twip_qa_{qa_name}")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"twip_qa_{qa_name}.parquet")
    tmp_path = out_path + ".tmp"
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, out_path)
    return out_path, df


def discover_tables(raw_dir=RAW_DIR):
    """Discover all TWIP tables in data/raw/."""
    tables = []
    for d in sorted(os.listdir(raw_dir)):
        dp = os.path.join(raw_dir, d)
        if not os.path.isdir(dp):
            continue
        if d.startswith("twip_qa_"):
            continue
        fp = os.path.join(dp, f"{d}.parquet")
        if os.path.exists(fp):
            tables.append(d)
    return tables


def run_all_tables(raw_dir=RAW_DIR):
    """Run QA for every table."""
    all_results = {}
    tables = discover_tables(raw_dir)

    for slug in tables:
        print(f"  QA: {slug}...", end=" ", flush=True)
        results = run_checks_for_table(slug, raw_dir)
        out_path, df = write_companion(slug, results, raw_dir)
        statuses = df["check_status"].value_counts().to_dict()
        status_str = " ".join(f"{k}={v}" for k, v in sorted(statuses.items()))
        print(f"{len(results)} checks: {status_str}")
        all_results[slug] = results

    return all_results


def print_summary(all_results):
    """Print aggregate summary."""
    totals = {"pass": 0, "warn": 0, "fail": 0, "error": 0}
    level_totals = {1: dict(totals), 2: dict(totals), 3: dict(totals)}
    issues = []

    for slug, results in all_results.items():
        for r in results:
            status = r["check_status"]
            level = r["check_level"]
            totals[status] = totals.get(status, 0) + 1
            if level in level_totals:
                level_totals[level][status] = level_totals[level].get(status, 0) + 1
            if status in ("fail", "warn"):
                issues.append((slug, r["check_name"], r["check_value"], r["notes"]))

    print(f"\n{'='*70}")
    print("RETROACTIVE QA SUMMARY")
    print(f"{'='*70}")
    print(f"Tables processed: {len(all_results)}")
    print(f"\n{'Level':<8} {'PASS':<8} {'WARN':<8} {'FAIL':<8} {'ERROR':<8}")
    print("-" * 40)
    for lvl in [1, 2, 3]:
        t = level_totals[lvl]
        print(f"L{lvl:<7} {t['pass']:<8} {t['warn']:<8} {t['fail']:<8} {t['error']:<8}")
    print("-" * 40)
    print(f"{'Total':<8} {totals['pass']:<8} {totals['warn']:<8} {totals['fail']:<8} {totals['error']:<8}")

    if issues:
        print(f"\nISSUES REQUIRING REVIEW:")
        print(f"{'Table':<45} {'Check':<25} {'Value':<30}")
        print("-" * 100)
        for slug, check, value, notes in issues:
            print(f"{slug:<45} {check:<25} {value:<30}")
            if notes:
                print(f"  -> {notes[:90]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TWIP QA Runner")
    parser.add_argument("--table-slug", help="Run QA for a specific table")
    parser.add_argument("--all", action="store_true", help="Run QA for all tables")
    args = parser.parse_args()

    if args.all:
        print("Running retroactive QA for all TWIP tables...")
        all_results = run_all_tables()
        print_summary(all_results)
    elif args.table_slug:
        results = run_checks_for_table(args.table_slug)
        _, df = write_companion(args.table_slug, results)
        print(df.to_string(index=False))
    else:
        parser.print_help()
