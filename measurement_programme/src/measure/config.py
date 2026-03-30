from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    repo_url: str
    default_branch: str = "main"
    language: str = "python"


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    github_token: str | None
    defect_dataset_url: str | None
    dashboard_url: str

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db.sqlite3"

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    @property
    def datasets_dir(self) -> Path:
        return self.data_dir / "datasets"


def load_app_config() -> AppConfig:
    data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        data_dir=data_dir,
        github_token=os.getenv("GITHUB_TOKEN") or None,
        defect_dataset_url=os.getenv("DEFECT_DATASET_URL") or None,
        dashboard_url=os.getenv("DASHBOARD_URL", "http://localhost:8501"),
    )


def load_projects_config(path: str | Path = Path("config/projects.yaml")) -> dict[str, ProjectConfig]:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    projects = {}
    for name, cfg in raw.get("projects", {}).items():
        projects[name] = ProjectConfig(
            name=name,
            repo_url=cfg["repo_url"],
            default_branch=cfg.get("default_branch", "main"),
            language=cfg.get("language", "python"),
        )
    return projects
