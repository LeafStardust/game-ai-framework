from pathlib import Path

import pytest

from games.balatro.live.runtime import balatro_agent_attempts_toggle as toggle
from games.balatro.live.runtime import balatro_agent_toggle as base_toggle
from games.balatro.live.runtime.agent_control import BalatroAgentControl


def test_env_r5_attempt_launcher_consumes_canonical_singular_count():
    argv = ["toggle", "--attempt", "3", "--status"]

    assert toggle._consume_attempt(argv) == 3
    assert argv == ["toggle", "--status"]


@pytest.mark.parametrize("value", ["0", "-1", "nope"])
def test_env_r5_attempt_launcher_rejects_invalid_count(value):
    with pytest.raises(ValueError, match="--attempt requires a positive integer"):
        toggle._consume_attempt(["toggle", "--attempt", value])


def test_env_r5_attempt_launcher_rejects_retired_plural_selector():
    with pytest.raises(ValueError, match="--attempt is required"):
        toggle._consume_attempt(["toggle", "--attempts", "3"])


def test_env_r5_attempt_launcher_forwards_bounded_supervisor_without_monitor(
    monkeypatch,
):
    captured = {}

    def fake_toggle_agent(control, **kwargs):
        captured["control"] = control
        captured.update(kwargs)
        return "STARTING", 4242

    monkeypatch.setattr(base_toggle, "toggle_agent", fake_toggle_agent)
    monkeypatch.setattr(
        base_toggle.sys,
        "argv",
        ["balatro_agent_attempts_toggle", "--attempt", "1"],
    )

    assert toggle.main() == 0
    assert base_toggle.SUPERVISOR_MODULE.endswith("balatro_agent_supervisor_entry")
    assert captured["control"].directory == BalatroAgentControl(None).directory
    assert captured["launch_live_monitor"] is False


def test_env_r5_windows_launcher_routes_only_canonical_attempt_selector():
    launcher = (Path(__file__).parents[2] / "BalatroAgentToggle.bat").read_text(
        encoding="utf-8"
    )

    assert '"--attempt" goto attempt' in launcher
    assert '"--attempts"' not in launcher
    assert '"--one"' not in launcher
    assert '"--three"' not in launcher
    assert '"--five"' not in launcher


def test_env_r5_attempt_launcher_forwards_blind_start_parity_directory(
    tmp_path, monkeypatch
):
    launched = []

    class _Process:
        pid = 4242

    monkeypatch.setattr(
        base_toggle.subprocess,
        "Popen",
        lambda command, **_kwargs: launched.append(list(command)) or _Process(),
    )
    monkeypatch.setattr(base_toggle, "_repo_root", lambda: tmp_path)

    control = BalatroAgentControl(tmp_path / "control")
    parity_directory = str(tmp_path / "blind-start-parity")
    pid = base_toggle.start_agent(
        control,
        blind_start_parity_directory=parity_directory,
        launch_live_monitor=False,
    )

    assert pid == 4242
    assert launched == [
        [
            base_toggle.sys.executable,
            "-m",
            base_toggle.SUPERVISOR_MODULE,
            "--control-dir",
            str(control.directory),
            "--blind-start-parity-directory",
            parity_directory,
        ]
    ]


def test_env_r5_attempt_launcher_forwards_blind_skip_parity_directory(
    tmp_path, monkeypatch
):
    launched = []

    class _Process:
        pid = 4242

    monkeypatch.setattr(
        base_toggle.subprocess,
        "Popen",
        lambda command, **_kwargs: launched.append(list(command)) or _Process(),
    )
    monkeypatch.setattr(base_toggle, "_repo_root", lambda: tmp_path)

    control = BalatroAgentControl(tmp_path / "control")
    parity_directory = str(tmp_path / "blind-skip-parity")
    pid = base_toggle.start_agent(
        control,
        blind_skip_parity_directory=parity_directory,
        launch_live_monitor=False,
    )

    assert pid == 4242
    assert launched[0][-2:] == ["--blind-skip-parity-directory", parity_directory]


def test_env_r5_attempt_launcher_forwards_buffoon_pack_parity_directory(
    tmp_path, monkeypatch
):
    launched = []

    class _Process:
        pid = 4242

    monkeypatch.setattr(
        base_toggle.subprocess,
        "Popen",
        lambda command, **_kwargs: launched.append(list(command)) or _Process(),
    )
    monkeypatch.setattr(base_toggle, "_repo_root", lambda: tmp_path)

    control = BalatroAgentControl(tmp_path / "control")
    parity_directory = str(tmp_path / "buffoon-pack-parity")
    pid = base_toggle.start_agent(
        control,
        buffoon_pack_parity_directory=parity_directory,
        launch_live_monitor=False,
    )

    assert pid == 4242
    assert launched[0][-2:] == ["--buffoon-pack-parity-directory", parity_directory]


def test_env_r5_attempt_launcher_forwards_held_planet_parity_directory(
    tmp_path, monkeypatch
):
    launched = []

    class _Process:
        pid = 4242

    monkeypatch.setattr(
        base_toggle.subprocess,
        "Popen",
        lambda command, **_kwargs: launched.append(list(command)) or _Process(),
    )
    monkeypatch.setattr(base_toggle, "_repo_root", lambda: tmp_path)

    control = BalatroAgentControl(tmp_path / "control")
    parity_directory = str(tmp_path / "held-planet-parity")
    pid = base_toggle.start_agent(
        control,
        held_planet_parity_directory=parity_directory,
        launch_live_monitor=False,
    )

    assert pid == 4242
    assert launched[0][-2:] == ["--held-planet-parity-directory", parity_directory]
