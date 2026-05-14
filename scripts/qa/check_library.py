"""
TWIP Unified QA Check Library
Per P-QA-DESIGN-001 and P-TWIP-024. Mirrors CWIP's check_library.py.

Each check function returns a dict:
  {check_name, check_level, check_status, check_value, check_threshold, notes}

Status values: pass, warn, fail, error
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta


def _result(name, level, status, value, threshold, notes=""):
    return {
        "check_name": name,
        "check_level": level,
        "check_status": status,
        "check_value": str(value),
        "check_threshold": str(threshold),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Level 1 — Ingestion Validation
# ---------------------------------------------------------------------------

def check_pk_unique(df, pk_columns):
    """Primary key has no duplicates."""
    try:
        if isinstance(pk_columns, str):
            pk_columns = [pk_columns]
        dupes = df.duplicated(subset=pk_columns, keep=False).sum()
        status = "pass" if dupes == 0 else "fail"
        return _result("pk_unique", 1, status, f"{dupes} duplicates",
                        "0 duplicates", f"PK columns: {pk_columns}")
    except Exception as e:
        return _result("pk_unique", 1, "error", str(e), "0 duplicates")


def check_required_nonnull(df, required_cols, threshold=0.01):
    """Required columns have null rate below threshold."""
    try:
        issues = []
        for col in required_cols:
            if col not in df.columns:
                issues.append(f"{col} missing from DataFrame")
                continue
            null_rate = df[col].isna().mean()
            if null_rate > threshold:
                issues.append(f"{col}: {null_rate:.2%} null (threshold {threshold:.0%})")
        status = "pass" if not issues else "fail"
        value = f"{len(issues)} columns above threshold" if issues else "all below threshold"
        return _result("required_nonnull", 1, status, value,
                        f"null rate < {threshold:.0%}", "; ".join(issues[:5]))
    except Exception as e:
        return _result("required_nonnull", 1, "error", str(e),
                        f"null rate < {threshold:.0%}")


def check_date_range_sane(df, date_cols, max_future_months=6):
    """No date column has values more than N months in the future."""
    try:
        cutoff = pd.Timestamp.now() + pd.DateOffset(months=max_future_months)
        issues = []
        for col in date_cols:
            if col not in df.columns:
                continue
            s = pd.to_datetime(df[col], errors="coerce")
            future = s[s > cutoff]
            if len(future) > 0:
                issues.append(f"{col}: {len(future)} rows > {cutoff.date()}")
        status = "pass" if not issues else "fail"
        value = f"{len(issues)} columns with future dates" if issues else "all dates sane"
        return _result("date_range_sane", 1, status, value,
                        f"no dates > today + {max_future_months} months",
                        "; ".join(issues[:5]))
    except Exception as e:
        return _result("date_range_sane", 1, "error", str(e),
                        f"no dates > today + {max_future_months} months")


def check_boolean_not_uniform(df, bool_cols):
    """Boolean columns are not 100% one value."""
    try:
        uniform = []
        for col in bool_cols:
            if col not in df.columns:
                continue
            vals = df[col].dropna().unique()
            if len(vals) <= 1:
                uniform.append(f"{col}={vals[0] if len(vals) else 'empty'}")
        status = "pass" if not uniform else "warn"
        value = f"{len(uniform)} uniform boolean columns" if uniform else "all booleans have variation"
        return _result("boolean_not_uniform", 1, status, value,
                        "at least 2 distinct values per boolean", "; ".join(uniform[:5]))
    except Exception as e:
        return _result("boolean_not_uniform", 1, "error", str(e),
                        "at least 2 distinct values per boolean")


def check_identifier_columns_str(df, id_cols):
    """Identifier columns are str dtype."""
    try:
        non_str = []
        for col in id_cols:
            if col not in df.columns:
                continue
            dtype = str(df[col].dtype)
            if "str" not in dtype.lower() and "object" not in dtype.lower() and "string" not in dtype.lower():
                non_str.append(f"{col}: {dtype}")
        status = "pass" if not non_str else "fail"
        value = f"{len(non_str)} non-str ID columns" if non_str else "all ID columns are str"
        return _result("identifier_columns_str", 1, status, value,
                        "all str", "; ".join(non_str[:5]))
    except Exception as e:
        return _result("identifier_columns_str", 1, "error", str(e), "all str")


def check_schema_columns_present(df, expected_columns):
    """All expected columns exist in the DataFrame."""
    try:
        missing = [c for c in expected_columns if c not in df.columns]
        status = "pass" if not missing else "fail"
        value = f"{len(missing)} missing" if missing else "all present"
        notes = f"missing: {missing[:5]}" if missing else ""
        return _result("schema_match", 1, status, value,
                        "all expected columns present", notes)
    except Exception as e:
        return _result("schema_match", 1, "error", str(e),
                        "all expected columns present")


def check_row_count(df, expected_count, tolerance=0.01):
    """Row count within tolerance of expected."""
    try:
        actual = len(df)
        if expected_count == 0:
            status = "warn" if actual == 0 else "pass"
        else:
            ratio = abs(actual - expected_count) / expected_count
            status = "pass" if ratio <= tolerance else "warn"
        return _result("row_count", 1, status, f"{actual:,}",
                        f"{expected_count:,} +/- {tolerance:.0%}",
                        f"delta: {actual - expected_count:+,}")
    except Exception as e:
        return _result("row_count", 1, "error", str(e),
                        f"{expected_count:,} +/- {tolerance:.0%}")


# ---------------------------------------------------------------------------
# Level 2 — Referential Integrity
# ---------------------------------------------------------------------------

def check_fk_match_rate(df, fk_col, ref_df, ref_pk_col,
                         warn_threshold=0.99, fail_threshold=0.95):
    """FK values resolve to parent table PK."""
    try:
        if fk_col not in df.columns:
            return _result("fk_match_rate", 2, "error",
                            f"{fk_col} not in table", f">={warn_threshold:.0%}")
        fk_vals = df[fk_col].dropna()
        ref_vals = set(ref_df[ref_pk_col].dropna().unique())
        matched = fk_vals.isin(ref_vals).sum()
        rate = matched / len(fk_vals) if len(fk_vals) > 0 else 1.0
        orphans = len(fk_vals) - matched
        if rate >= warn_threshold:
            status = "pass"
        elif rate >= fail_threshold:
            status = "warn"
        else:
            status = "fail"
        return _result("fk_match_rate", 2, status, f"{rate:.2%} ({orphans:,} orphans)",
                        f">={warn_threshold:.0%}", f"{fk_col} -> {ref_pk_col}")
    except Exception as e:
        return _result("fk_match_rate", 2, "error", str(e),
                        f">={warn_threshold:.0%}")


def check_cardinality_bounds(df, group_col, max_expected):
    """Max group size within expected bounds."""
    try:
        if group_col not in df.columns:
            return _result("cardinality_bounds", 2, "error",
                            f"{group_col} not in table", f"max <= {max_expected}")
        sizes = df.groupby(group_col).size()
        max_size = sizes.max()
        status = "pass" if max_size <= max_expected else "warn"
        top = sizes.nlargest(3)
        notes = f"top groups: {dict(top)}"
        return _result("cardinality_bounds", 2, status, f"max group: {max_size:,}",
                        f"max <= {max_expected:,}", notes)
    except Exception as e:
        return _result("cardinality_bounds", 2, "error", str(e),
                        f"max <= {max_expected}")


def check_dtype_consistency(tables_info, column_name):
    """Same column name has same dtype across all tables that contain it."""
    try:
        dtypes_found = {}
        for slug, df in tables_info.items():
            if column_name in df.columns:
                dtypes_found[slug] = str(df[column_name].dtype)
        unique_dtypes = set(dtypes_found.values())
        status = "pass" if len(unique_dtypes) <= 1 else "fail"
        return _result("dtype_consistency", 2, status,
                        f"{len(unique_dtypes)} distinct dtypes for '{column_name}'",
                        "1 dtype across all tables",
                        f"dtypes: {dtypes_found}" if len(unique_dtypes) > 1 else "")
    except Exception as e:
        return _result("dtype_consistency", 2, "error", str(e),
                        "1 dtype across all tables")


# ---------------------------------------------------------------------------
# Level 3 — Analytical Sanity
# ---------------------------------------------------------------------------

def check_count_sanity(actual_count, min_expected, max_expected, entity_name):
    """Total count within expected range."""
    try:
        status = "pass" if min_expected <= actual_count <= max_expected else "fail"
        return _result("count_sanity", 3, status, f"{actual_count:,} {entity_name}",
                        f"{min_expected:,}-{max_expected:,}",
                        "within range" if status == "pass" else "outside range")
    except Exception as e:
        return _result("count_sanity", 3, "error", str(e),
                        f"{min_expected:,}-{max_expected:,}")
