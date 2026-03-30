from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GreenProxy:
    sustainability_proxy_index: float
    power_indicator_loc_x_cc: float


def compute_green_proxies(loc: int, cc_avg: float, churn_24h: int) -> GreenProxy:
    # Normalize gently to keep values stable
    # These are *proxies* used for a sustainability-style dashboard section.
    n_loc = loc / 10_000.0
    n_cc = cc_avg / 10.0
    n_churn = churn_24h / 5_000.0

    sustainability_proxy_index = float(n_loc + n_cc + n_churn)
    power_indicator = float(loc * cc_avg)

    return GreenProxy(
        sustainability_proxy_index=sustainability_proxy_index,
        power_indicator_loc_x_cc=power_indicator,
    )
