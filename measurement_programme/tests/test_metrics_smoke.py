from measure.metrics.static_metrics import compute_static_repo_metrics

def test_static_metrics_smoke():
    m = compute_static_repo_metrics(["def x():\n  return 1\n"])
    assert m.loc >= 1
    assert m.cc_avg >= 0
