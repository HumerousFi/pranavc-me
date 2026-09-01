from update_metrics import merge_metrics

NOW = "2026-09-02T00:00:00Z"


def base_resume():
    return {
        "projects": [{"id": "webguardian"}],
        "metrics": {"generatedAt": None, "github": None, "projects": {}},
    }


def test_merge_metrics_populates_successful_fetches():
    resume = base_resume()
    repo_results = {"webguardian": {"data": {"stars": 3, "last_commit_sha": "abc1234"}}}
    user_result = {"data": {"public_repos": 30, "followers": 10}}

    updated = merge_metrics(resume, repo_results, user_result, NOW)

    assert updated["metrics"]["generatedAt"] == NOW
    assert updated["metrics"]["github"] == {"public_repos": 30, "followers": 10, "fetched_at": NOW}
    assert updated["metrics"]["projects"]["webguardian"]["stars"] == 3
    assert updated["metrics"]["projects"]["webguardian"]["fetched_at"] == NOW


def test_merge_metrics_does_not_mutate_input():
    resume = base_resume()
    original = {"stars": 1}
    resume["metrics"]["projects"]["webguardian"] = original

    merge_metrics(resume, {"webguardian": {"data": {"stars": 99}}}, {"data": {}}, NOW)

    assert resume["metrics"]["projects"]["webguardian"] == original


def test_merge_metrics_keeps_prior_data_on_failed_fetch():
    resume = base_resume()
    resume["metrics"]["projects"]["webguardian"] = {"stars": 5, "fetched_at": "2026-08-01T00:00:00Z"}

    updated = merge_metrics(
        resume,
        {"webguardian": {"error": "GET .../webguardian -> 500"}},
        {"data": {"public_repos": 30, "followers": 10}},
        NOW,
    )

    project_metrics = updated["metrics"]["projects"]["webguardian"]
    # the old, real number survives - it is not wiped back to null just
    # because this run's fetch failed
    assert project_metrics["stars"] == 5
    assert project_metrics["error"] == "GET .../webguardian -> 500"
    assert project_metrics["attempted_at"] == NOW


def test_merge_metrics_failed_fetch_is_distinguishable_from_a_real_zero():
    resume = base_resume()

    updated = merge_metrics(
        resume, {"webguardian": {"error": "network unreachable"}}, {"data": {}}, NOW
    )

    project_metrics = updated["metrics"]["projects"]["webguardian"]
    assert "error" in project_metrics
    assert "stars" not in project_metrics  # never silently defaulted to 0


def test_merge_metrics_user_fetch_failure_keeps_prior_github_block():
    resume = base_resume()
    resume["metrics"]["github"] = {"public_repos": 30, "followers": 10, "fetched_at": "2026-08-01T00:00:00Z"}

    updated = merge_metrics(resume, {}, {"error": "rate limited"}, NOW)

    assert updated["metrics"]["github"]["public_repos"] == 30
    assert updated["metrics"]["github"]["error"] == "rate limited"


def test_merge_metrics_handles_multiple_projects_independently():
    resume = base_resume()
    resume["projects"].append({"id": "homelab-as-code"})

    updated = merge_metrics(
        resume,
        {
            "webguardian": {"data": {"stars": 1}},
            "homelab-as-code": {"error": "404"},
        },
        {"data": {"public_repos": 30, "followers": 10}},
        NOW,
    )

    assert updated["metrics"]["projects"]["webguardian"]["stars"] == 1
    assert "error" in updated["metrics"]["projects"]["homelab-as-code"]
