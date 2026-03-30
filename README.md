# Measurement Program (Daily Metrics + Dashboard)

## What it does
- Collects static metrics from Python source code (LOC, complexity, Halstead, MI, OO approximations, CAAEC)
- Collects process metrics daily (commits, churn, issues)
- Optional defect-dataset evaluation metrics (AUC-ROC, MCC, F1) from an open CSV dataset
- Stores results in SQLite
- Streamlit dashboard + daily screenshots
- Runs AIMQ-inspired information quality checks

## Quickstart
1) Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

2) Run
```bash
Terminal 1:
bash scripts/run_daily.sh

Terminal 2:
streamlit run app.py
```
