from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
import pandas as pd


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  project TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  git_sha TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS measurements (
  run_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL,
  unit TEXT,
  scope TEXT,         -- repo / file / class / function / dataset
  entity TEXT,        -- filename or class/function name if applicable
  meta_json TEXT,
  PRIMARY KEY (run_id, metric, scope, entity)
);

CREATE TABLE IF NOT EXISTS iq_checks (
  run_id TEXT NOT NULL,
  check_name TEXT NOT NULL,
  passed INTEGER NOT NULL,
  severity TEXT NOT NULL,  -- info/warn/error
  details TEXT,
  PRIMARY KEY (run_id, check_name)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def upsert_run(con: sqlite3.Connection, run: dict[str, Any]) -> None:
    con.execute(
        "INSERT OR REPLACE INTO runs(run_id, project, collected_at, git_sha, notes) VALUES(?,?,?,?,?)",
        (run["run_id"], run["project"], run["collected_at"], run.get("git_sha"), run.get("notes")),
    )
    con.commit()


def upsert_measurements(con: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO measurements(run_id, metric, value, unit, scope, entity, meta_json) VALUES(?,?,?,?,?,?,?)",
        [
            (
                r["run_id"],
                r["metric"],
                r.get("value"),
                r.get("unit"),
                r.get("scope", "repo"),
                r.get("entity", ""),
                r.get("meta_json"),
            )
            for r in rows
        ],
    )
    con.commit()


def upsert_iq_checks(con: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO iq_checks(run_id, check_name, passed, severity, details) VALUES(?,?,?,?,?)",
        [
            (r["run_id"], r["check_name"], int(r["passed"]), r["severity"], r.get("details"))
            for r in rows
        ],
    )
    con.commit()


def read_df(con: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, con, params=params)
