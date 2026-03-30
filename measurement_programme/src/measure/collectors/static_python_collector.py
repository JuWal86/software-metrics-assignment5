from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class PythonFile:
    path: Path
    relpath: str
    text: str


def iter_python_files(repo_path: Path) -> Iterable[PythonFile]:
    for p in repo_path.rglob("*.py"):
        if any(part.startswith(".") for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(p.relative_to(repo_path))
        yield PythonFile(path=p, relpath=rel, text=text)
