from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from git import Repo


@dataclass
class GitProcessData:
    head_sha: str
    commits_24h: int
    churn_added_24h: int
    churn_deleted_24h: int


def get_repo(repo_path: Path) -> Repo:
    return Repo(str(repo_path))


def collect_git_process(repo_path: Path) -> GitProcessData:
    repo = get_repo(repo_path)
    head_sha = repo.head.commit.hexsha

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    commits = list(repo.iter_commits(rev="HEAD", since=since.isoformat()))
    commits_24h = len(commits)

    added = 0
    deleted = 0
    for c in commits:
        stats = c.stats.total
        added += int(stats.get("insertions", 0))
        deleted += int(stats.get("deletions", 0))

    return GitProcessData(
        head_sha=head_sha,
        commits_24h=commits_24h,
        churn_added_24h=added,
        churn_deleted_24h=deleted,
    )
