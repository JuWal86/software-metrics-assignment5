from __future__ import annotations

import argparse
from rich import print

from .config import load_app_config, load_projects_config
from .runner import run_project


def main() -> None:
    parser = argparse.ArgumentParser(prog="measure")
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run a daily measurement collection")
    r.add_argument("--project", required=True, help="Project key from config/projects.yaml")

    args = parser.parse_args()

    app = load_app_config()
    projects = load_projects_config()

    if args.project not in projects:
        raise SystemExit(f"Unknown project '{args.project}'. Available: {list(projects.keys())}")

    run_id = run_project(app, projects[args.project])
    print(f"[green]OK[/green] run_id={run_id}")
