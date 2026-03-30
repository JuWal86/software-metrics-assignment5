from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from github import Github


@dataclass
class GitHubIssueData:
    open_issues: int
    median_time_to_close_days_30d: float | None


def parse_repo_full_name(repo_url: str) -> str:
    # https://github.com/owner/repo(.git)
    s = repo_url.rstrip("/")
    if s.endswith(".git"):
        s = s[:-4]
    return "/".join(s.split("/")[-2:])


def collect_github_issue_metrics(repo_url: str, token: Optional[str]) -> GitHubIssueData:
    gh = Github(login_or_token=token) if token else Github()
    full_name = parse_repo_full_name(repo_url)
    repo = gh.get_repo(full_name)

    open_issues = repo.open_issues_count

    # median time-to-close among issues closed in last 30 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    closed = repo.get_issues(state="closed", since=cutoff)

    durations = []
    for issue in closed:
        # skip PRs (GitHub API exposes PRs via issues)
        if issue.pull_request is not None:
            continue
        if issue.closed_at and issue.created_at:
            durations.append((issue.closed_at - issue.created_at).total_seconds() / 86400.0)

    if not durations:
        median = None
    else:
        durations.sort()
        n = len(durations)
        median = durations[n // 2] if n % 2 == 1 else (durations[n // 2 - 1] + durations[n // 2]) / 2

    return GitHubIssueData(open_issues=open_issues, median_time_to_close_days_30d=median)
