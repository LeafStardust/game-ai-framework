from pathlib import Path

import pytest

from games.balatro.live.runtime import balatro_agent_attempts_toggle as toggle


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


def test_env_r5_windows_launcher_routes_only_canonical_attempt_selector():
    launcher = (Path(__file__).parents[2] / "BalatroAgentToggle.bat").read_text(
        encoding="utf-8"
    )

    assert '"--attempt" goto attempt' in launcher
    assert '"--attempts"' not in launcher
    assert '"--one"' not in launcher
    assert '"--three"' not in launcher
    assert '"--five"' not in launcher
