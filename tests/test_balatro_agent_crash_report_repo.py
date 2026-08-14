from pathlib import Path

from games.balatro.live.external import balatro_agent_crash_report_repo as report_repo


def test_default_crash_report_path_is_repo_local_and_git_ignored_by_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(report_repo, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(report_repo, "_stamp", lambda: "20260814T070000Z")

    path = report_repo.default_repo_crash_report_path()

    assert path == (
        tmp_path
        / "logs"
        / "balatro"
        / "crash-reports"
        / "balatro-agent-crash-20260814T070000Z.log"
    )
    assert path.suffix == ".log"
    assert Path("logs/balatro/crash-reports") in path.parents
