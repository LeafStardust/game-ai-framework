import sys

import pytest

from games.mahjong_soul.live.__main__ import main


@pytest.mark.parametrize("target", ["", "!python", "game,python", "*", "local:game"])
def test_process_capture_rejects_broad_or_invalid_target(monkeypatch, target):
    monkeypatch.setattr(sys, "argv", ["capture", "--process", target, "--check"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
