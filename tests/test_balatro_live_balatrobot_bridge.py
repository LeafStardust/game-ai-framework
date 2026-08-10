import pytest

from games.balatro.actions import (
    BUY_CONSUMABLE,
    DISCARD_CARDS,
    END_ROUND,
    END_SHOP,
    PLAY_CARDS,
    REFRESH_SHOP,
    USE_CONSUMABLE,
)
from games.balatro.live import (
    BalatroBotBridge,
    BalatroBotRpcError,
    LiveBalatroCommand,
)


class Requester:

    def __init__(self):
        self.calls = []
        self.responses = []

    def __call__(self, endpoint, payload, timeout):
        self.calls.append((endpoint, payload, timeout))
        if self.responses:
            return self.responses.pop(0)
        return {
            "jsonrpc": "2.0",
            "result": {},
            "id": payload["id"],
        }


def test_balatrobot_bridge_observes_gamestate():
    requester = Requester()
    requester.responses.append(
        {
            "jsonrpc": "2.0",
            "result": {
                "state": "SELECTING_HAND",
                "money": 4,
            },
            "id": 1,
        }
    )
    bridge = BalatroBotBridge(requester=requester)

    snapshot = bridge.observe()

    assert snapshot.sequence == 1
    assert snapshot.phase == "SELECTING_HAND"
    assert snapshot.state_complete
    assert snapshot.payload["money"] == 4
    assert requester.calls[0][1]["method"] == "gamestate"


def test_balatrobot_bridge_sequence_changes_only_with_state():
    requester = Requester()
    state = {
        "state": "SHOP",
        "money": 5,
    }
    requester.responses.extend(
        [
            {"jsonrpc": "2.0", "result": state, "id": 1},
            {"jsonrpc": "2.0", "result": state, "id": 2},
            {
                "jsonrpc": "2.0",
                "result": {
                    "state": "SHOP",
                    "money": 6,
                },
                "id": 3,
            },
        ]
    )
    bridge = BalatroBotBridge(requester=requester)

    first = bridge.observe()
    second = bridge.observe()
    third = bridge.observe()

    assert first.sequence == 1
    assert second.sequence == 1
    assert third.sequence == 2


def test_balatrobot_bridge_maps_live_actions_to_rpc_methods():
    requester = Requester()
    requester.responses.extend(
        [
            {"jsonrpc": "2.0", "result": {"state": "SELECTING_HAND"}, "id": 1},
            {"jsonrpc": "2.0", "result": {"state": "SELECTING_HAND"}, "id": 2},
            {"jsonrpc": "2.0", "result": {"state": "SHOP"}, "id": 3},
            {"jsonrpc": "2.0", "result": {"state": "SHOP"}, "id": 4},
            {"jsonrpc": "2.0", "result": {"state": "BLIND_SELECT"}, "id": 5},
            {"jsonrpc": "2.0", "result": {"state": "SHOP"}, "id": 6},
            {"jsonrpc": "2.0", "result": {"state": "SELECTING_HAND"}, "id": 7},
        ]
    )
    bridge = BalatroBotBridge(requester=requester)

    commands = [
        LiveBalatroCommand(1, PLAY_CARDS, {"cards": [0, 2]}),
        LiveBalatroCommand(2, DISCARD_CARDS, {"cards": [1]}),
        LiveBalatroCommand(3, BUY_CONSUMABLE, {"target": 0}),
        LiveBalatroCommand(4, REFRESH_SHOP),
        LiveBalatroCommand(5, END_SHOP),
        LiveBalatroCommand(6, END_ROUND),
        LiveBalatroCommand(
            7,
            USE_CONSUMABLE,
            {"target": 1, "cards": [0, 3]},
        ),
    ]

    for command in commands:
        bridge.send(command)

    requests = [call[1] for call in requester.calls]

    assert requests[0]["method"] == "play"
    assert requests[0]["params"] == {"cards": [0, 2]}
    assert requests[1]["method"] == "discard"
    assert requests[1]["params"] == {"cards": [1]}
    assert requests[2]["method"] == "buy"
    assert requests[2]["params"] == {"card": 0}
    assert requests[3]["method"] == "reroll"
    assert requests[4]["method"] == "next_round"
    assert requests[5]["method"] == "cash_out"
    assert requests[6]["method"] == "use"
    assert requests[6]["params"] == {
        "consumable": 1,
        "cards": [0, 3],
    }


def test_balatrobot_bridge_health_check_reports_connection():
    requester = Requester()
    requester.responses.append(
        {
            "jsonrpc": "2.0",
            "result": {"status": "ok"},
            "id": 1,
        }
    )

    assert BalatroBotBridge(requester=requester).is_connected()


def test_balatrobot_bridge_raises_rpc_errors():
    requester = Requester()
    requester.responses.append(
        {
            "jsonrpc": "2.0",
            "error": {
                "code": -32001,
                "message": "wrong game state",
                "data": {"name": "INVALID_STATE"},
            },
            "id": 1,
        }
    )
    bridge = BalatroBotBridge(requester=requester)

    with pytest.raises(BalatroBotRpcError) as error:
        bridge.call("select")

    assert error.value.code == -32001
    assert error.value.data["name"] == "INVALID_STATE"
