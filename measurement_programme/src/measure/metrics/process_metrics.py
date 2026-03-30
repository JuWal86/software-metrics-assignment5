from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessMetrics:
    commits_24h: int
    churn_24h: int
    open_issues: int
    median_time_to_close_days_30d: float | None
