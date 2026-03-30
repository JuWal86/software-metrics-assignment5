from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from git import Repo

from .config import AppConfig, ProjectConfig
from .db import connect, init_db, upsert_run, upsert_measurements, upsert_iq_checks

from .collectors.static_python_collector import iter_python_files
from .collectors.git_collector import collect_git_process
from .collectors.github_collector import collect_github_issue_metrics
from .collectors.defect_dataset_collector import load_defect_dataset

from .metrics.static_metrics import compute_static_repo_metrics
from .metrics.oo_metrics import compute_oo_metrics
from .metrics.exceptions_metrics import compute_caaec
from .metrics.smells_metrics import compute_smells
from .metrics.green_proxy_metrics import compute_green_proxies
from .metrics.defect_prediction_metrics import compute_defect_prediction_scores
from .quality.aimq_checks import run_aimq_checks


def ensure_cloned(project: ProjectConfig, projects_dir: Path) -> Path:
    projects_dir.mkdir(parents=True, exist_ok=True)
    target = projects_dir / project.name
    if not target.exists():
        Repo.clone_from(project.repo_url, str(target))
    else:
        repo = Repo(str(target))
        repo.remotes.origin.fetch()
        # attempt fast-forward
        try:
            repo.git.checkout(project.default_branch)
        except Exception:
            pass
        try:
            repo.git.pull("--ff-only")
        except Exception:
            # if local has no branch name match, just keep current
            pass
    return target


def run_project(app: AppConfig, project: ProjectConfig) -> str:
    t0 = time.time()
    collected_at = datetime.now(timezone.utc)

    repo_path = ensure_cloned(project, app.projects_dir)

    # process metrics (git)
    git_data = collect_git_process(repo_path)

    # static source
    py_files = list(iter_python_files(repo_path))
    texts = [f.text for f in py_files]
    static = compute_static_repo_metrics(texts)

    # OO metrics (per class)
    py_texts = [(f.relpath, f.text) for f in py_files]
    class_oo = compute_oo_metrics(py_texts)
    class_exc = compute_caaec(py_texts)

    # smells (repo indicators derived from per-class)
    smells = compute_smells(class_oo, static.loc)

    # github metrics
    github_used = True
    gh = collect_github_issue_metrics(project.repo_url, app.github_token)

    # green proxies
    churn_24h = git_data.churn_added_24h + git_data.churn_deleted_24h
    green = compute_green_proxies(static.loc, static.cc_avg, churn_24h)

    # optional defect dataset metrics (AUC/MCC/F1)
    defect_scores = None
    if app.defect_dataset_url:
        ds = load_defect_dataset(app.defect_dataset_url, app.datasets_dir)
        defect_scores = compute_defect_prediction_scores(ds.df, label_col="bug")

    run_id = str(uuid.uuid4())

    con = connect(app.db_path)
    init_db(con)
    upsert_run(
        con,
        dict(
            run_id=run_id,
            project=project.name,
            collected_at=collected_at.isoformat(),
            git_sha=git_data.head_sha,
            notes="",
        ),
    )

    rows: list[dict] = []

    # repo-level static
    rows += [
        {"run_id": run_id, "metric": "loc", "value": static.loc, "unit": "loc", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "cc_avg", "value": static.cc_avg, "unit": "cc", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "cc_p95", "value": static.cc_p95, "unit": "cc", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "cc_max", "value": static.cc_max, "unit": "cc", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "halstead_volume", "value": static.halstead_volume, "unit": "volume", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "halstead_effort", "value": static.halstead_effort, "unit": "effort", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "maintainability_index", "value": static.maintainability_index, "unit": "mi", "scope": "repo", "entity": ""},
    ]

    # process
    rows += [
        {"run_id": run_id, "metric": "commits_24h", "value": git_data.commits_24h, "unit": "count", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "churn_added_24h", "value": git_data.churn_added_24h, "unit": "lines", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "churn_deleted_24h", "value": git_data.churn_deleted_24h, "unit": "lines", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "churn_24h", "value": churn_24h, "unit": "lines", "scope": "repo", "entity": ""},
    ]

    # github
    rows += [
        {"run_id": run_id, "metric": "open_issues", "value": gh.open_issues, "unit": "count", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "median_time_to_close_days_30d", "value": (gh.median_time_to_close_days_30d or None), "unit": "days", "scope": "repo", "entity": ""},
    ]

    # smells
    rows += [
        {"run_id": run_id, "metric": "long_method_ratio", "value": smells.long_method_ratio, "unit": "ratio", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "god_class_ratio", "value": smells.god_class_ratio, "unit": "ratio", "scope": "repo", "entity": ""},
    ]

    # green proxies
    rows += [
        {"run_id": run_id, "metric": "sustainability_proxy_index", "value": green.sustainability_proxy_index, "unit": "index", "scope": "repo", "entity": ""},
        {"run_id": run_id, "metric": "power_indicator_loc_x_cc", "value": green.power_indicator_loc_x_cc, "unit": "loc*cc", "scope": "repo", "entity": ""},
    ]

    # per-class OO metrics
    for cls, m in class_oo.items():
        rows += [
            {"run_id": run_id, "metric": "wmc", "value": m.wmc, "unit": "cc-sum", "scope": "class", "entity": cls},
            {"run_id": run_id, "metric": "dit", "value": m.dit, "unit": "levels", "scope": "class", "entity": cls},
            {"run_id": run_id, "metric": "noc", "value": m.noc, "unit": "count", "scope": "class", "entity": cls},
            {"run_id": run_id, "metric": "cbo", "value": m.cbo, "unit": "count", "scope": "class", "entity": cls},
            {"run_id": run_id, "metric": "lcom", "value": m.lcom, "unit": "ratio", "scope": "class", "entity": cls},
        ]

    # per-class exceptions (CAAEC)
    for cls, m in class_exc.items():
        rows.append({"run_id": run_id, "metric": "caaec", "value": m.caaec, "unit": "handlers/method", "scope": "class", "entity": cls})

    # defect evaluation metrics (dataset scope)
    if defect_scores is not None:
        rows += [
            {"run_id": run_id, "metric": "auc_roc", "value": defect_scores.auc_roc, "unit": "auc", "scope": "dataset", "entity": "defect_dataset"},
            {"run_id": run_id, "metric": "mcc", "value": defect_scores.mcc, "unit": "mcc", "scope": "dataset", "entity": "defect_dataset"},
            {"run_id": run_id, "metric": "f1", "value": defect_scores.f1, "unit": "f1", "scope": "dataset", "entity": "defect_dataset"},
        ]

    upsert_measurements(con, rows)

    # AIMQ checks
    runtime = time.time() - t0
    mdf = pd.DataFrame(
        [{"metric": r["metric"], "value": r.get("value"), "unit": r.get("unit"), "scope": r.get("scope"), "entity": r.get("entity")} for r in rows]
    )

    expected = {
        "loc", "cc_avg", "halstead_volume", "maintainability_index",
        "commits_24h", "churn_24h", "open_issues", "median_time_to_close_days_30d",
        "long_method_ratio", "god_class_ratio", "sustainability_proxy_index", "power_indicator_loc_x_cc",
        "caaec", "wmc", "dit"
    }
    # If defect dataset enabled, expect these too:
    if app.defect_dataset_url:
        expected |= {"auc_roc", "mcc", "f1"}

    iq = run_aimq_checks(
        collected_at=collected_at,
        measurements=mdf,
        expected_metrics=expected,
        runtime_seconds=runtime,
        github_used=github_used,
        token_present=bool(app.github_token),
    )
    upsert_iq_checks(
        con,
        [
            dict(run_id=run_id, check_name=x.check_name, passed=x.passed, severity=x.severity, details=x.details)
            for x in iq
        ],
    )
    con.close()

    return run_id
