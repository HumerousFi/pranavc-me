from unittest.mock import Mock, patch

from github_api import fetch_repo_stats, fetch_user_stats


def make_response(status_code=200, json_data=None):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


@patch("github_api.requests.get")
def test_fetch_repo_stats_success(mock_get):
    repo_json = {"stargazers_count": 3, "open_issues_count": 1, "pushed_at": "2026-09-01T00:00:00Z"}
    commits_json = [{"sha": "abcdef1234567890", "commit": {"message": "Fix a bug\n\nlonger body"}}]
    mock_get.side_effect = [make_response(200, repo_json), make_response(200, commits_json)]

    result = fetch_repo_stats("HumerousFi", "webguardian")

    assert "error" not in result
    assert result["data"]["stars"] == 3
    assert result["data"]["last_commit_sha"] == "abcdef1"
    assert result["data"]["last_commit_message"] == "Fix a bug"


@patch("github_api.requests.get")
def test_fetch_repo_stats_repo_not_found(mock_get):
    mock_get.return_value = make_response(404, {"message": "Not Found"})

    result = fetch_repo_stats("HumerousFi", "does-not-exist")

    assert "error" in result
    assert "404" in result["error"]


@patch("github_api.requests.get")
def test_fetch_repo_stats_commits_call_fails_is_still_an_error(mock_get):
    repo_json = {"stargazers_count": 3, "open_issues_count": 1, "pushed_at": "2026-09-01T00:00:00Z"}
    mock_get.side_effect = [make_response(200, repo_json), make_response(403, {"message": "rate limited"})]

    result = fetch_repo_stats("HumerousFi", "webguardian")

    assert "error" in result


@patch("github_api.requests.get")
def test_fetch_repo_stats_network_exception_is_an_error_not_a_crash(mock_get):
    import requests

    mock_get.side_effect = requests.ConnectionError("boom")

    result = fetch_repo_stats("HumerousFi", "webguardian")

    assert "error" in result


@patch("github_api.requests.get")
def test_fetch_repo_stats_no_commits_yet(mock_get):
    repo_json = {"stargazers_count": 0, "open_issues_count": 0, "pushed_at": None}
    mock_get.side_effect = [make_response(200, repo_json), make_response(200, [])]

    result = fetch_repo_stats("HumerousFi", "empty-repo")

    assert result["data"]["last_commit_sha"] is None
    assert result["data"]["last_commit_message"] is None


@patch("github_api.requests.get")
def test_fetch_user_stats_success(mock_get):
    mock_get.return_value = make_response(200, {"public_repos": 30, "followers": 10})

    result = fetch_user_stats("HumerousFi")

    assert result["data"] == {"public_repos": 30, "followers": 10}


@patch("github_api.requests.get")
def test_fetch_user_stats_failure(mock_get):
    mock_get.return_value = make_response(500, {})

    result = fetch_user_stats("HumerousFi")

    assert "error" in result


@patch("github_api.requests.get")
def test_authenticated_request_sends_bearer_header(mock_get):
    mock_get.return_value = make_response(200, {"public_repos": 1, "followers": 1})

    fetch_user_stats("HumerousFi", token="secret-token")

    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"


@patch("github_api.requests.get")
def test_unauthenticated_request_omits_auth_header(mock_get):
    mock_get.return_value = make_response(200, {"public_repos": 1, "followers": 1})

    fetch_user_stats("HumerousFi", token=None)

    _, kwargs = mock_get.call_args
    assert "Authorization" not in kwargs["headers"]
