from agents.red_deck_agent import RedDeckAgent
from games.balatro.actions import PLAY_CARDS
from games.balatro.live import BalatroBotBridge
from games.balatro.live.runner import BalatroLiveRunner


class FirstPlayAgent:

    def __init__(self):
        self.decisions = 0

    def act(self, state, actions):
        self.decisions += 1
        return next(
            action
            for action in actions
            if action.name == PLAY_CARDS
        )


class SilentTelemetry:

    def __init__(self):
        self.actions = []
        self.finished = None

    def run_started(self, snapshot, state):
        pass

    def state_observed(self, snapshot, state):
        pass

    def decision(self, action, state):
        self.actions.append(action.name)

    def error(self, error):
        raise AssertionError(f"unexpected telemetry error: {error}")

    def run_finished(self, snapshot, state, outcome=None):
        self.finished = snapshot


def game_state(phase, won=False, with_hand=False):
    hand_cards = []
    if with_hand:
        hand_cards = [
            {
                "id": 1,
                "key": "H_A",
                "set": "DEFAULT",
                "value": {"suit": "H", "rank": "A"},
                "modifier": {},
            },
            {
                "id": 2,
                "key": "S_K",
                "set": "DEFAULT",
                "value": {"suit": "S", "rank": "K"},
                "modifier": {},
            },
        ]

    return {
        "state": phase,
        "round_num": 1,
        "ante_num": 1,
        "money": 4,
        "deck": "RED",
        "stake": "WHITE",
        "seed": "TEST",
        "won": won,
        "round": {
            "hands_left": 4,
            "discards_left": 4,
            "chips": 0,
        },
        "blinds": {
            "small": {
                "type": "SMALL",
                "status": "CURRENT",
                "name": "Small Blind",
                "score": 300,
            }
        },
        "hand": {
            "count": len(hand_cards),
            "limit": 8,
            "cards": hand_cards,
        },
        "cards": {
            "count": len(hand_cards),
            "limit": 52,
            "cards": hand_cards,
        },
        "consumables": {
            "count": 0,
            "limit": 2,
            "cards": [],
        },
        "shop": {
            "count": 0,
            "limit": 2,
            "cards": [],
        },
        "hands": {},
    }


def test_live_runner_operates_complete_phase_loop_without_manual_input():
    calls = []

    def requester(endpoint, request, timeout):
        method = request["method"]
        calls.append((method, request.get("params")))

        states = {
            "menu": game_state("MENU"),
            "start": game_state("BLIND_SELECT"),
            "select": game_state("SELECTING_HAND", with_hand=True),
            "play": game_state("ROUND_EVAL"),
            "cash_out": game_state("SHOP"),
            "next_round": game_state("GAME_OVER", won=False),
        }
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": states[method],
        }

    bridge = BalatroBotBridge(requester=requester)
    agent = FirstPlayAgent()
    telemetry = SilentTelemetry()
    runner = BalatroLiveRunner(
        bridge=bridge,
        agent=agent,
        telemetry=telemetry,
        poll_interval=0,
    )

    won = runner.run(seed="TEST")

    assert not won
    assert agent.decisions == 1
    assert telemetry.finished.phase == "GAME_OVER"
    assert telemetry.actions == [
        "SELECT_BLIND",
        PLAY_CARDS,
        "END_ROUND",
        "END_SHOP",
    ]
    assert [method for method, _ in calls] == [
        "menu",
        "start",
        "select",
        "play",
        "cash_out",
        "next_round",
    ]
    assert calls[1][1] == {
        "deck": "RED",
        "stake": "WHITE",
        "seed": "TEST",
    }


def test_live_runner_defaults_to_red_deck_agent():
    runner = BalatroLiveRunner(
        bridge=BalatroBotBridge(
            requester=lambda endpoint, request, timeout: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"status": "ok"},
            }
        ),
        telemetry=SilentTelemetry(),
    )

    assert isinstance(runner.agent, RedDeckAgent)
