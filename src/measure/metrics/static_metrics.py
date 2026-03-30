from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit


@dataclass
class StaticRepoMetrics:
    loc: int
    cc_avg: float
    cc_p95: float
    cc_max: float
    halstead_volume: float
    halstead_effort: float
    maintainability_index: float


def compute_loc(texts: list[str]) -> int:
    loc = 0
    for t in texts:
        for line in t.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            loc += 1
    return loc


def compute_static_repo_metrics(texts: list[str]) -> StaticRepoMetrics:
    loc = compute_loc(texts)

    # Cyclomatic complexity per block
    ccs = []
    for t in texts:
        try:
            blocks = cc_visit(t)
            ccs.extend([b.complexity for b in blocks])
        except Exception:
            continue

    if ccs:
        ccs_sorted = sorted(ccs)
        cc_avg = sum(ccs) / len(ccs)
        cc_max = float(max(ccs))
        idx = int(0.95 * (len(ccs_sorted) - 1))
        cc_p95 = float(ccs_sorted[idx])
    else:
        cc_avg = cc_p95 = cc_max = 0.0

    # Halstead (aggregate)
    volumes = []
    efforts = []
    for t in texts:
        try:
            h = h_visit(t)
            if h.total:
                volumes.append(float(h.total.volume))
                efforts.append(float(h.total.effort))
        except Exception:
            continue

    halstead_volume = float(sum(volumes)) if volumes else 0.0
    halstead_effort = float(sum(efforts)) if efforts else 0.0

    # Maintainability Index (radon provides MI per file; aggregate mean)
    mis = []
    for t in texts:
        try:
            mis.append(float(mi_visit(t, multi=True)))
        except Exception:
            continue
    maintainability_index = float(sum(mis) / len(mis)) if mis else 0.0

    return StaticRepoMetrics(
        loc=loc,
        cc_avg=float(cc_avg),
        cc_p95=float(cc_p95),
        cc_max=float(cc_max),
        halstead_volume=halstead_volume,
        halstead_effort=halstead_effort,
        maintainability_index=maintainability_index,
    )
