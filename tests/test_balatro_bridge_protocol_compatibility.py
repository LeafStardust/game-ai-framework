from games.balatro.live.injected.bridge import (
    BRIDGE_PROTOCOL_VERSION,
    normalize_bridge_status,
)


def test_known_command_pump_revision_normalizes_to_protocol_one():
    status = normalize_bridge_status(
        {
            "bridge": "2",
            "achievement_gate": "ENABLED",
            "restart_run_callback": "START_RUN_PRESENT",
            "command_pump": "LOVE_RUN_PRE_UPDATE",
        }
    )

    assert status["bridge"] == BRIDGE_PROTOCOL_VERSION == "1"
    assert status["bridge_revision"] == "2"
    assert status["command_pump"] == "LOVE_RUN_PRE_UPDATE"


def test_protocol_one_status_is_unchanged():
    status = normalize_bridge_status(
        {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }
    )

    assert status == {
        "bridge": "1",
        "achievement_gate": "ENABLED",
    }


def test_unknown_future_bridge_version_remains_fail_closed():
    status = normalize_bridge_status(
        {
            "bridge": "3",
            "achievement_gate": "ENABLED",
            "command_pump": "SOMETHING_NEW",
        }
    )

    assert status["bridge"] == "3"
    assert "bridge_revision" not in status


def test_bridge_two_without_known_pump_signature_is_not_normalized():
    status = normalize_bridge_status(
        {
            "bridge": "2",
            "achievement_gate": "ENABLED",
        }
    )

    assert status["bridge"] == "2"
    assert "bridge_revision" not in status
