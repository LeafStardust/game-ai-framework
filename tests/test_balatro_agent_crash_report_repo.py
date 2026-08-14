from games.balatro.live.external import balatro_agent_crash_report_repo as report_repo


def test_default_crash_report_path_is_repo_local_and_git_ignored_by_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(report_repo, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(report_repo, "_stamp", lambda: "20260814T070000Z")

    path = report_repo.default_repo_crash_report_path()
    directory = tmp_path / "logs" / "balatro" / "crash-reports"

    assert path == directory / "balatro-agent-crash-20260814T070000Z.log"
    assert path.parent == directory
    assert path.suffix == ".log"
