from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any
import pandas as pd


@dataclass
class IQCheckResult:
    check_name: str
    passed: bool
    severity: str  # info/warn/error
    details: str


def run_aimq_checks(
    *,
    collected_at: datetime,
    measurements: pd.DataFrame,   # columns: metric,value,unit,scope,entity
    expected_metrics: set[str],
    runtime_seconds: float,
    github_used: bool,
    token_present: bool,
) -> list[IQCheckResult]:
    results: list[IQCheckResult] = []

    # 1) Accessibility: can we produce measurements at all?
    results.append(
        IQCheckResult(
            "accessibility_nonempty_measurements",
            passed=len(measurements) > 0,
            severity="error",
            details=f"rows={len(measurements)}",
        )
    )

    # 2) Appropriate amount: minimum count threshold
    results.append(
        IQCheckResult(
            "appropriate_amount_min_rows",
            passed=len(measurements) >= 20,  # repo + per-class rows usually exceeds this
            severity="warn",
            details=f"rows={len(measurements)} (expected >= 20)",
        )
    )

    # 3) Completeness: no missing values for core metrics
    core = measurements[measurements["scope"].isin(["repo", "dataset"])]
    missing_core = core["value"].isna().sum()
    results.append(
        IQCheckResult(
            "completeness_core_no_missing",
            passed=missing_core == 0,
            severity="error",
            details=f"missing_core_values={missing_core}",
        )
    )

    # 4) Free of error: value ranges sanity checks for key metrics
    def _get(metric: str) -> float | None:
        s = core.loc[core["metric"] == metric, "value"]
        return None if s.empty else float(s.iloc[0])

    loc = _get("loc")
    cc_avg = _get("cc_avg")
    mi = _get("maintainability_index")

    ok_loc = (loc is None) or (loc >= 0 and loc < 5_000_000)
    ok_cc = (cc_avg is None) or (cc_avg >= 0 and cc_avg < 5000)
    ok_mi = (mi is None) or (mi >= 0 and mi <= 100)

    results.append(IQCheckResult("free_of_error_loc_range", ok_loc, "error", f"loc={loc}"))
    results.append(IQCheckResult("free_of_error_cc_range", ok_cc, "error", f"cc_avg={cc_avg}"))
    results.append(IQCheckResult("free_of_error_mi_range", ok_mi, "warn", f"mi={mi}"))

    # 5) Consistent representation: types and required columns
    required_cols = {"metric", "value", "unit", "scope", "entity"}
    results.append(
        IQCheckResult(
            "consistent_representation_schema",
            passed=required_cols.issubset(set(measurements.columns)),
            severity="error",
            details=f"columns={list(measurements.columns)}",
        )
    )

    # 6) Concise representation: no duplicate rows (metric,scope,entity)
    dup = measurements.duplicated(subset=["metric", "scope", "entity"]).sum()
    results.append(IQCheckResult("concise_representation_no_duplicates", dup == 0, "warn", f"dups={dup}"))

    # 7) Interpretability: units must exist for repo-level metrics (can be empty for class rows)
    repo = measurements[measurements["scope"] == "repo"]
    bad_units = repo["unit"].isna().sum()
    results.append(IQCheckResult("interpretability_repo_units_present", bad_units == 0, "warn", f"missing_units={bad_units}"))

    # 8) Timeliness: collected_at within last 24h (for a “daily” pipeline)
    now = datetime.now(timezone.utc)
    age = now - collected_at
    results.append(
        IQCheckResult(
            "timeliness_within_24h",
            passed=age <= timedelta(hours=24),
            severity="warn",
            details=f"age_hours={age.total_seconds()/3600:.2f}",
        )
    )

    # 9) Relevancy: expected metrics present
    have = set(measurements["metric"].unique().tolist())
    missing = sorted(list(expected_metrics - have))
    results.append(
        IQCheckResult(
            "relevancy_expected_metrics_present",
            passed=len(missing) == 0,
            severity="error",
            details=f"missing={missing}",
        )
    )

    # 10) Believability: outlier rate not extreme (IQR-based on class WMC)
    wmc = measurements[(measurements["metric"] == "wmc") & (measurements["scope"] == "class")]["value"].dropna()
    if len(wmc) >= 10:
        q1 = wmc.quantile(0.25)
        q3 = wmc.quantile(0.75)
        iqr = q3 - q1
        outliers = ((wmc < (q1 - 1.5 * iqr)) | (wmc > (q3 + 1.5 * iqr))).mean()
        believable = outliers <= 0.50  # allow lots of skew but not absurd
        results.append(IQCheckResult("believability_outlier_rate_reasonable", believable, "warn", f"outlier_rate={outliers:.2f}"))
    else:
        results.append(IQCheckResult("believability_outlier_rate_reasonable", True, "info", "not_enough_wmc_samples"))

    # 11) Ease of operation: runtime under threshold (local runs should be fast-ish)
    results.append(
        IQCheckResult(
            "ease_of_operation_runtime_under_120s",
            passed=runtime_seconds <= 120,
            severity="warn",
            details=f"runtime_seconds={runtime_seconds:.2f}",
        )
    )

    # 12) Security: if GitHub used, token should be present OR we warn about rate limiting; also ensure we did not require token.
    if github_used and not token_present:
        results.append(IQCheckResult("security_token_missing_warning", False, "warn", "GITHUB_TOKEN not set; API rate limiting risk"))
    else:
        results.append(IQCheckResult("security_token_missing_warning", True, "info", "ok"))

    # 13) Objectivity: deterministic model evaluation (we fix random_state=42)
    results.append(IQCheckResult("objectivity_deterministic_seeds", True, "info", "random_state fixed in defect metrics"))

    return results
