import pytest

from games.balatro.live import (
    BalatroActionExecutor,
    BalatroLiveBridge,
    BalatroStateTranslator,
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


def test_live_snapshot_defaults_to_empty_payload():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="ROUND_START",
        state_complete=True,
    )

    assert snapshot.payload == {}


def test_live_command_defaults_to_empty_payload():
    command = LiveBalatroCommand(
        sequence=1,
        action="PLAY_CARDS",
    )

    assert command.payload == {}


def test_live_integration_interfaces_are_abstract():
    with pytest.raises(TypeError):
        BalatroLiveBridge()

    with pytest.raises(TypeError):
        BalatroStateTranslator()

    with pytest.raises(TypeError):
        BalatroActionExecutor()
