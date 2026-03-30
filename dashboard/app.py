from __future__ import annotations

from datetime import datetime
import streamlit as st
import pandas as pd

from measure.config import load_app_config
from measure.db import connect, init_db, read_df


st.set_page_config(page_title="Measurement Dashboard", layout="wide")

# 1. Charger la config de base (pour les tokens et URLs)
base_config = load_app_config()

# 2. CORRIGER LE CHEMIN : On pointe vers le dossier 'data' à la racine du projet
# __file__ = .../dashboard/app.py
# .parent = .../dashboard/
# .parent = .../measurement_programme/ (racine)
# / "data" = .../measurement_programme/data/
from pathlib import Path
correct_data_dir = Path(__file__).parent.parent / "data"

# 3. Recréer l'objet AppConfig avec le bon chemin de données
from measure.config import AppConfig
app = AppConfig(
    data_dir=correct_data_dir,
    github_token=base_config.github_token,
    defect_dataset_url=base_config.defect_dataset_url,
    dashboard_url=base_config.dashboard_url
)

# 4. Connexion à la BONNE base de données
con = connect(app.db_path)
init_db(con)

st.title("Daily Measurement Dashboard")

projects = read_df(con, "SELECT DISTINCT project FROM runs ORDER BY project")["project"].tolist()
project = st.selectbox("Project", projects) if projects else None

if not project:
    st.info("No runs yet. Run: `measure run --project <name>`")
    st.stop()

runs = read_df(
    con,
    "SELECT run_id, collected_at, git_sha FROM runs WHERE project=? ORDER BY collected_at DESC LIMIT 30",
    (project,),
)
latest_run_id = runs["run_id"].iloc[0]

m = read_df(con, "SELECT * FROM measurements WHERE run_id=?", (latest_run_id,))
iq = read_df(con, "SELECT * FROM iq_checks WHERE run_id=? ORDER BY severity DESC, passed ASC", (latest_run_id,))

st.subheader("Latest Run")
st.write(f"Run: `{latest_run_id}`  |  Collected: `{runs['collected_at'].iloc[0]}`  |  SHA: `{runs['git_sha'].iloc[0]}`")

col1, col2, col3 = st.columns(3)

def metric_value(metric: str):
    s = m[(m["metric"] == metric) & (m["scope"] == "repo")]["value"]
    return None if s.empty else float(s.iloc[0])

with col1:
    st.metric("LOC", metric_value("loc"))
    st.metric("CC avg", metric_value("cc_avg"))
    st.metric("Maintainability Index", metric_value("maintainability_index"))

with col2:
    st.metric("Commits (24h)", metric_value("commits_24h"))
    st.metric("Churn (24h)", metric_value("churn_24h"))
    st.metric("Open issues", metric_value("open_issues"))

with col3:
    st.metric("Median time-to-close (30d, days)", metric_value("median_time_to_close_days_30d"))
    st.metric("Sustainability Proxy Index", metric_value("sustainability_proxy_index"))
    st.metric("Power Indicator (LOC×CCavg)", metric_value("power_indicator_loc_x_cc"))

st.subheader("Smell Indicators")
st.write(
    m[(m["metric"].isin(["long_method_ratio", "god_class_ratio"])) & (m["scope"] == "repo")][["metric", "value", "unit"]]
)

st.subheader("Top Classes by WMC (complexity proxy)")
top_wmc = m[(m["metric"] == "wmc") & (m["scope"] == "class")].sort_values("value", ascending=False).head(20)
st.dataframe(top_wmc[["entity", "value"]], use_container_width=True)

st.subheader("CAAEC (Top Classes by Exception Handling Density)")
top_caaec = m[(m["metric"] == "caaec") & (m["scope"] == "class")].sort_values("value", ascending=False).head(20)
st.dataframe(top_caaec[["entity", "value"]], use_container_width=True)

st.subheader("Defect Dataset Scores (if configured)")
ds = m[m["scope"] == "dataset"][["metric", "value", "unit", "entity"]]
if ds.empty:
    st.info("No defect dataset configured. Set DEFECT_DATASET_URL in .env to compute AUC/MCC/F1.")
else:
    st.dataframe(ds, use_container_width=True)

st.subheader("Information Quality Checks (AIMQ-inspired)")
st.dataframe(iq[["check_name", "passed", "severity", "details"]], use_container_width=True)

st.subheader("History (Repo-level metrics)")
repo_metrics = m[m["scope"] == "repo"]["metric"].unique().tolist()
metric_to_plot = st.selectbox("Metric", sorted(repo_metrics))

hist = read_df(
    con,
    """
    SELECT r.collected_at, m.value
    FROM runs r
    JOIN measurements m ON m.run_id = r.run_id
    WHERE r.project=? AND m.metric=? AND m.scope='repo'
    ORDER BY r.collected_at ASC
    """,
    (project, metric_to_plot),
)
if not hist.empty:
    hist["collected_at"] = pd.to_datetime(hist["collected_at"])
    st.line_chart(hist.set_index("collected_at")["value"])

con.close()
