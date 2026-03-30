from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from .oo_metrics import ClassOOMetrics


@dataclass
class SmellIndicators:
    long_method_ratio: float      # % functions with high complexity (approx)
    god_class_ratio: float        # % classes with high WMC/size proxy


def compute_smells(class_metrics: Dict[str, ClassOOMetrics], loc: int) -> SmellIndicators:
    # Heuristics that work on many OSS repos:
    # God Class: WMC >= 50 (approx) OR very high coupling
    # Long Method: we approximate using WMC distribution (since we did not store per-function CC)
    if not class_metrics:
        return SmellIndicators(long_method_ratio=0.0, god_class_ratio=0.0)

    wmc_values = [m.wmc for m in class_metrics.values()]
    wmc_values.sort()
    p90 = wmc_values[int(0.9 * (len(wmc_values) - 1))] if len(wmc_values) > 1 else wmc_values[0]
    # long method proxy: classes above p90 (conservative)
    long_method_ratio = sum(1 for v in wmc_values if v >= max(30.0, p90)) / len(wmc_values)

    god_class_ratio = sum(1 for m in class_metrics.values() if (m.wmc >= 50.0 or m.cbo >= 25)) / len(class_metrics)

    return SmellIndicators(long_method_ratio=float(long_method_ratio), god_class_ratio=float(god_class_ratio))
