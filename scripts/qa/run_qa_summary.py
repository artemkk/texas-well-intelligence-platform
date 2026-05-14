"""
TWIP QA Summary Runner
Per P-TWIP-025. Scans all twip_qa_*.parquet companion tables, computes
latest status per (table, check), writes twip_qa_summary.parquet,
generates review queue for new FAILs/WARNs.

Usage:
    python scripts/qa/run_qa_summary.py
"""

import os
import sys
import pandas as pd
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(REPO_ROOT, "data", "raw")
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
PRODUCT = "twip"
QA_PREFIX = "twip_qa_"
SUMMARY_DIR = os.path.join(RAW_DIR, "twip_qa_summary")
SUMMARY_FILE = os.path.join(SUMMARY_DIR, "twip_qa_summary.parquet")


def discover_companion_tables():
    """Find all twip_qa_*.parquet companion tables in data/raw/."""
    tables = {}
    for d in sorted(os.listdir(RAW_DIR)):
        if not d.startswith(QA_PREFIX):
            continue
        if d == "twip_qa_summary":
            continue
        fp = os.path.join(RAW_DIR, d, f"{d}.parquet")
        if os.path.exists(fp):
            slug = d.replace(QA_PREFIX, "")
            tables[slug] = fp
    return tables


def load_previous_summary():
    """Load previous qa_summary if it exists."""
    if os.path.exists(SUMMARY_FILE):
        return pd.read_parquet(SUMMARY_FILE)
    return None


def build_summary(companions):
    """Build summary from all companion tables."""
    rows = []
    for slug, path in companions.items():
        try:
            df = pd.read_parquet(path)
            if df.empty:
                continue
            for check_name in df["check_name"].unique():
                check_rows = df[df["check_name"] == check_name]
                latest = check_rows.sort_values("checked_at", ascending=False).iloc[0]
                rows.append({
                    "table_slug": slug,
                    "check_name": latest["check_name"],
                    "check_level": int(latest["check_level"]),
                    "latest_status": latest["check_status"],
                    "latest_value": latest.get("check_value", ""),
                    "latest_threshold": latest.get("check_threshold", ""),
                    "latest_checked_at": latest["checked_at"],
                    "latest_run_id": latest["ingestion_run_id"],
                    "notes": latest.get("notes", ""),
                })
        except Exception as e:
            rows.append({
                "table_slug": slug,
                "check_name": "_read_error",
                "check_level": 0,
                "latest_status": "error",
                "latest_value": str(e),
                "latest_threshold": "",
                "latest_checked_at": datetime.now(timezone.utc).isoformat(),
                "latest_run_id": "",
                "notes": f"Failed to read {path}",
            })
    return pd.DataFrame(rows)


def find_new_issues(current_summary, previous_summary):
    """Identify new FAILs and WARNs since last run."""
    issues = current_summary[
        current_summary["latest_status"].isin(["fail", "warn"])
    ].copy()

    if previous_summary is not None and not previous_summary.empty:
        prev_lookup = {}
        for _, row in previous_summary.iterrows():
            key = (row["table_slug"], row["check_name"])
            prev_lookup[key] = row.get("latest_status", "")

        new_flags = []
        for _, row in issues.iterrows():
            key = (row["table_slug"], row["check_name"])
            prev_status = prev_lookup.get(key, "")
            is_new = prev_status != row["latest_status"]
            new_flags.append(is_new)
        issues["is_new"] = new_flags
    else:
        issues["is_new"] = True

    return issues


def write_review_queue(issues, run_date):
    """Write markdown review queue file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    queue_path = os.path.join(LOGS_DIR, f"qa_review_queue_{run_date}.md")

    lines = [
        f"# TWIP QA Review Queue — {run_date}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Total issues: {len(issues)} ({issues['is_new'].sum()} new)",
        "",
        "---",
        "",
    ]

    if issues.empty:
        lines.append("No FAILs or WARNs. All checks passing.")
    else:
        for _, row in issues.iterrows():
            marker = "**NEW**" if row["is_new"] else "existing"
            lines.append(f"### {row['table_slug']} / {row['check_name']} [{marker}]")
            lines.append("")
            lines.append(f"- **Status:** {row['latest_status'].upper()}")
            lines.append(f"- **Level:** {row['check_level']}")
            lines.append(f"- **Value:** {row['latest_value']}")
            lines.append(f"- **Threshold:** {row['latest_threshold']}")
            if row.get("notes"):
                lines.append(f"- **Notes:** {row['notes']}")
            lines.append(f"- **Checked at:** {row['latest_checked_at']}")
            lines.append("")

    with open(queue_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return queue_path


def main():
    now = datetime.now(timezone.utc)
    run_date = now.strftime("%Y%m%d")

    print(f"TWIP QA Summary Runner — {now.isoformat()}")
    print("=" * 60)

    companions = discover_companion_tables()
    print(f"Companion tables found: {len(companions)}")

    prev = load_previous_summary()
    if prev is not None:
        print(f"Previous summary loaded: {len(prev)} rows")
    else:
        print("No previous summary (first run)")

    summary = build_summary(companions)
    print(f"Current summary: {len(summary)} (table, check) tuples")

    status_counts = summary["latest_status"].value_counts().to_dict()
    print(f"Status breakdown: {status_counts}")

    # Write summary (atomic)
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    tmp = SUMMARY_FILE + ".tmp"
    summary.to_parquet(tmp, index=False)
    os.replace(tmp, SUMMARY_FILE)
    print(f"Summary written: {SUMMARY_FILE}")

    issues = find_new_issues(summary, prev)
    print(f"Issues (FAIL/WARN): {len(issues)} total, {issues['is_new'].sum()} new")

    queue_path = write_review_queue(issues, run_date)
    print(f"Review queue: {queue_path}")

    if not issues.empty:
        print(f"\n{'Table':<40} {'Check':<25} {'Status':<8} {'New?':<5}")
        print("-" * 80)
        for _, row in issues.iterrows():
            new_mark = "NEW" if row["is_new"] else ""
            print(f"{row['table_slug']:<40} {row['check_name']:<25} {row['latest_status']:<8} {new_mark:<5}")

    log_path = os.path.join(LOGS_DIR, "qa_summary_runner.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{now.isoformat()} | companions={len(companions)} | "
                f"tuples={len(summary)} | {status_counts} | "
                f"issues={len(issues)} new={issues['is_new'].sum()}\n")

    print(f"\nLog appended: {log_path}")
    print("Done.")


if __name__ == "__main__":
    main()
