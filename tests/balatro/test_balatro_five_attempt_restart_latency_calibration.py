from games.balatro.live.runtime import balatro_agent_five_attempts_entry as entry


def test_five_attempt_restart_timeout_is_bounded_to_latest_telemetry_window():
    assert entry.FIVE_ATTEMPT_RESTART_TIMEOUT_SECONDS == 15.0


def test_five_attempt_restart_passes_calibrated_timeout(monkeypatch):
    captured = {}

    def fake_restart(runner, deck, stake, *, timeout_seconds):
        captured.update(
            runner=runner,
            deck=deck,
            stake=stake,
            timeout_seconds=timeout_seconds,
        )
        return "ready"

    monkeypatch.setattr(entry, "restart_fresh_unseeded_run", fake_restart)
    runner = object()

    result = entry._five_attempt_restart(runner, "RED", "WHITE")

    assert result == "ready"
    assert captured == {
        "runner": runner,
        "deck": "RED",
        "stake": "WHITE",
        "timeout_seconds": 15.0,
    }
