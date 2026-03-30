from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, matthews_corrcoef


@dataclass
class DefectPredictionScores:
    auc_roc: float
    mcc: float
    f1: float


def compute_defect_prediction_scores(df: pd.DataFrame, label_col: str = "bug") -> DefectPredictionScores:
    if label_col not in df.columns:
        raise ValueError(f"Defect dataset must have label column '{label_col}' (0/1).")

    y = df[label_col].astype(int)
    X = df.drop(columns=[label_col])

    # keep numeric only
    X = X.select_dtypes(include=["number"]).fillna(0.0)
    if X.shape[1] == 0:
        raise ValueError("Defect dataset has no numeric feature columns.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
        ]
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    auc = float(roc_auc_score(y_test, proba)) if y_test.nunique() > 1 else 0.0
    f1 = float(f1_score(y_test, pred, zero_division=0))
    mcc = float(matthews_corrcoef(y_test, pred)) if y_test.nunique() > 1 else 0.0

    return DefectPredictionScores(auc_roc=auc, mcc=mcc, f1=f1)
