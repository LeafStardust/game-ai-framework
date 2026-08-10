from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live import (
    BalatroConsoleTelemetry,
    LiveBalatroSnapshot,
)
from games.balatro.state import BalatroState


class Logger:

    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(("INFO", message % args))

    def warning(self, message, *args):
        self.messages.append(("WARNING", message % args))

    def error(self, message, *args):
        self.messages.append(("ERROR", message % args))


def live_state():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = 2
    state.round = 4
    state.money = 11
    state.blind_score = 300
    state.hands_remaining = 2
    state.discards_remaining = 1
    state.blind = Blind(BlindType.BIG, 600)
    return state


def test_telemetry_logs_run_state_and_decision():
    logger = Logger()
    telemetry = BalatroConsoleTelemetry(logger)
    state = live_state()
    snapshot = LiveBalatroSnapshot(
        sequence=7,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"seed": "ABC123"},
    )
    action = BalatroAction(
        PLAY_CARDS,
        cards=[
            BalatroCard("A", "Spades", live_id=0),
            BalatroCard("K", "Hearts", live_id=1),
        ],
    )

    telemetry.run_started(snapshot, state)
    telemetry.decision(action, state)

    messages = [message for _, message in logger.messages]

    assert any("RUN START" in message for message in messages)
    assert any("score=300/600 (50.0%)" in message for message in messages)
    assert any("DECISION #1 | PLAY_CARDS" in message for message in messages)
    assert any("cards=[AS,KH]" in message for message in messages)
    assert telemetry.stats.decisions == 1
    assert telemetry.stats.actions[PLAY_CARDS] == 1


def test_telemetry_tracks_recoveries_errors_and_run_summary():
    logger = Logger()
    telemetry = BalatroConsoleTelemetry(logger)
    state = live_state()
    snapshot = LiveBalatroSnapshot(
        sequence=9,
        phase="GAME_OVER",
        state_complete=True,
        payload={"won": False},
    )

    telemetry.recovery("stale state", snapshot)
    telemetry.error(RuntimeError("boom"))
    telemetry.run_finished(snapshot, state)

    messages = [message for _, message in logger.messages]

    assert telemetry.stats.recoveries == 1
    assert telemetry.stats.errors == 1
    assert any("RECOVERY #1" in message for message in messages)
    assert any("ERROR #1" in message for message in messages)
    assert any("RUN END | outcome=LOSS" in message for message in messages)
    assert any("max_ante=2" in message for message in messages)
