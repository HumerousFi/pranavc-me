"""Fetches live GitHub metrics and merges them into resume.json.

Run standalone:  python scripts/update_metrics.py [path/to/resume.json]
Reads GITHUB_TOKEN from the environment if set (GitHub Actions provides
this automatically; without it you're limited to 60 unauthenticated
requests/hour, which is fine for local testing with this few repos).
"""

from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from github_api import fetch_repo_stats, fetch_user_stats

DEFAULT_RESUME_PATH = Path(__file__).parent.parent / "resume.json"
GITHUB_USERNAME = "HumerousFi"


def merge_metrics(resume: dict, repo_results: dict[str, dict], user_result: dict, now: str) -> dict:
    """Returns a new resume dict with resume["metrics"] updated.

    Does not mutate the input. A failed fetch for a given key keeps
    whatever metrics were already recorded there (annotated with the
    error and when the fetch was attempted) rather than overwriting good
    data with nulls - a stale-but-real number is more useful than a wiped
    one, and either way it must be distinguishable from a successful
    zero, not silently indistinguishable from it.
    """
    result = copy.deepcopy(resume)
    metrics = result.setdefault("metrics", {})
    metrics["generatedAt"] = now

    if "error" in user_result:
        existing = metrics.get("github") or {}
        metrics["github"] = {**existing, "error": user_result["error"], "attempted_at": now}
    else:
        metrics["github"] = {**user_result["data"], "fetched_at": now}

    projects_metrics = metrics.setdefault("projects", {})
    for project_id, fetch_result in repo_results.items():
        if "error" in fetch_result:
            existing = projects_metrics.get(project_id) or {}
            projects_metrics[project_id] = {
                **existing,
                "error": fetch_result["error"],
                "attempted_at": now,
            }
        else:
            projects_metrics[project_id] = {**fetch_result["data"], "fetched_at": now}

    return result


def run(resume_path: Path, token: str | None) -> int:
    with open(resume_path) as f:
        resume = json.load(f)

    repo_results: dict[str, dict] = {}
    for project in resume.get("projects", []):
        gh = project.get("github")
        if not gh:
            continue
        repo_results[project["id"]] = fetch_repo_stats(gh["owner"], gh["repo"], token=token)

    user_result = fetch_user_stats(GITHUB_USERNAME, token=token)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = merge_metrics(resume, repo_results, user_result, now)

    with open(resume_path, "w") as f:
        json.dump(updated, f, indent=2)
        f.write("\n")

    failures = [pid for pid, r in repo_results.items() if "error" in r]
    if "error" in user_result:
        failures.append("(user stats)")
    if failures:
        print(f"Updated {resume_path} with {len(failures)} fetch failure(s): {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"Updated {resume_path}: {len(repo_results)} project(s), user stats OK")
    return 0


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RESUME_PATH
    sys.exit(run(path, token=os.environ.get("GITHUB_TOKEN")))
