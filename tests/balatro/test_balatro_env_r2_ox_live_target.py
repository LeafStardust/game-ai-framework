from games.balatro.live import DefaultBalatroStateTranslator, LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import (
    snapshot_payload_from_live_memory,
)
from games.balatro.live.runtime.luajit_memory import LuaValue


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[address]

    def array_items(self, address):
        return ()


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _snapshot_payload(current_round):
    game_address = 100
    current_round_address = 101
    decoder = _FakeDecoder(
        {
            game_address: {"current_round": _table(current_round_address)},
            current_round_address: current_round,
        }
    )
    payload, _, _ = snapshot_payload_from_live_memory(
        decoder,
        {"GAME": _table(game_address)},
    )
    return payload


def _translate(payload):
    return DefaultBalatroStateTranslator().translate(
        LiveBalatroSnapshot(
            sequence=1,
            phase="SELECTING_HAND",
            state_complete=True,
            payload=payload,
        )
    )


def test_env_r2_ox_live_observer_exposes_fixed_round_most_played_hand():
    payload = _snapshot_payload(
        {"most_played_poker_hand": _string("Pair")}
    )

    assert payload["round"]["most_played_poker_hand"] == "Pair"


def test_env_r2_ox_live_observer_omits_missing_or_nonstring_target():
    missing = _snapshot_payload({})
    invalid = _snapshot_payload({"most_played_poker_hand": _integer(3)})

    assert "most_played_poker_hand" not in missing["round"]
    assert "most_played_poker_hand" not in invalid["round"]


def test_env_r2_ox_translator_maps_live_hand_name_to_canonical_name():
    state = _translate(
        {"round": {"most_played_poker_hand": "Pair"}}
    )

    assert state.round_most_played_hand == "PAIR"


def test_env_r2_ox_translator_preserves_unknown_when_target_is_absent():
    state = _translate({"round": {}})

    assert state.round_most_played_hand is None
