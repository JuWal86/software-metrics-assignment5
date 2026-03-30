from datetime import datetime, timezone
import pandas as pd
from measure.quality.aimq_checks import run_aimq_checks

def test_aimq_checks_smoke():
    df = pd.DataFrame([
        {"metric":"loc","value":10,"unit":"loc","scope":"repo","entity":""},
        {"metric":"cc_avg","value":2,"unit":"cc","scope":"repo","entity":""},
        {"metric":"maintainability_index","value":80,"unit":"mi","scope":"repo","entity":""},
        {"metric":"commits_24h","value":1,"unit":"count","scope":"repo","entity":""},
        {"metric":"churn_24h","value":5,"unit":"lines","scope":"repo","entity":""},
        {"metric":"open_issues","value":1,"unit":"count","scope":"repo","entity":""},
        {"metric":"median_time_to_close_days_30d","value":2,"unit":"days","scope":"repo","entity":""},
        {"metric":"long_method_ratio","value":0.1,"unit":"ratio","scope":"repo","entity":""},
        {"metric":"god_class_ratio","value":0.05,"unit":"ratio","scope":"repo","entity":""},
        {"metric":"sustainability_proxy_index","value":0.5,"unit":"index","scope":"repo","entity":""},
        {"metric":"power_indicator_loc_x_cc","value":20,"unit":"loc*cc","scope":"repo","entity":""},
        {"metric":"wmc","value":10,"unit":"cc-sum","scope":"class","entity":"A"},
        {"metric":"dit","value":0,"unit":"levels","scope":"class","entity":"A"},
        {"metric":"caaec","value":0,"unit":"handlers/method","scope":"class","entity":"A"},
    ])
    expected = set(df["metric"].unique())
    out = run_aimq_checks(
        collected_at=datetime.now(timezone.utc),
        measurements=df,
        expected_metrics=expected,
        runtime_seconds=1.0,
        github_used=False,
        token_present=False,
    )
    assert len(out) >= 10
