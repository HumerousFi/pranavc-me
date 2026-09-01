"""Thin wrapper around the GitHub REST API for the two calls this pipeline
needs: per-repo stats and per-user stats.

Each function returns {"data": {...}} on success or {"error": "..."} on
failure - never raises for an ordinary HTTP error, and never returns a
success-shaped dict for a failure. That distinction matters here for the
same reason it mattered in webguardian: a failed fetch must not look
identical to "fetched fine, the real number is just small/zero".
"""

from __future__ import annotations

import requests

API_ROOT = "https://api.github.com"
TIMEOUT = 10


def _headers(token: str | None) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_repo_stats(owner: str, repo: str, token: str | None = None) -> dict:
    headers = _headers(token)
    try:
        repo_resp = requests.get(f"{API_ROOT}/repos/{owner}/{repo}", headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return {"error": f"request failed: {exc}"}

    if repo_resp.status_code != 200:
        return {"error": f"GET /repos/{owner}/{repo} -> {repo_resp.status_code}"}

    repo_json = repo_resp.json()

    try:
        commits_resp = requests.get(
            f"{API_ROOT}/repos/{owner}/{repo}/commits",
            headers=headers,
            params={"per_page": 1},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"error": f"request failed: {exc}"}

    if commits_resp.status_code != 200:
        return {"error": f"GET /repos/{owner}/{repo}/commits -> {commits_resp.status_code}"}

    commits_json = commits_resp.json()
    last_commit = commits_json[0] if commits_json else None

    return {
        "data": {
            "stars": repo_json.get("stargazers_count"),
            "open_issues": repo_json.get("open_issues_count"),
            "pushed_at": repo_json.get("pushed_at"),
            "last_commit_sha": last_commit["sha"][:7] if last_commit else None,
            "last_commit_message": (
                last_commit["commit"]["message"].splitlines()[0] if last_commit else None
            ),
        }
    }


def fetch_user_stats(username: str, token: str | None = None) -> dict:
    headers = _headers(token)
    try:
        resp = requests.get(f"{API_ROOT}/users/{username}", headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return {"error": f"request failed: {exc}"}

    if resp.status_code != 200:
        return {"error": f"GET /users/{username} -> {resp.status_code}"}

    data = resp.json()
    return {
        "data": {
            "public_repos": data.get("public_repos"),
            "followers": data.get("followers"),
        }
    }
