import pytest

from games.balatro.live.external.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
    native_pack_ready,
    native_round_eval_ready,
    native_selecting_hand_ready,
)
from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.protocol import LiveBalatroSnapshot


def _table(address: int) -> LuaValue:
    return LuaValue("table", address, 0)


def _function(address: int = 1) -> LuaValue:
    return LuaValue("function", address, 0)


def _boolean(value: bool) -> LuaValue:
    return LuaValue("boolean", value, 0)


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[int(address)]


def _native_fixture():
    tables = {
        10: {"cards": _table(11)},
        20: {"UIRoot": _table(21)},
        30: {
            "play_cards_from_highlighted": _function(31),
            "discard_cards_from_highlighted": _function(32),
            "use_card": _function(33),
            "cash_out": _function(34),
            "skip_booster": _function(35),
        },
        40: {
            "cards": _table(41),
            "REMOVED": _boolean(False),
        },
    }
    root = {
        "hand": _table(10),
        "buttons": _table(20),
        "FUNCS": _table(30),
        "pack_cards": _table(40),
    }
    return _Decoder(tables), root, tables


def test_selecting_hand_readiness_requires_native_controls_and_callbacks():
    decoder, root, tables = _native_fixture()

    assert native_selecting_hand_ready(decoder, root)

    tables[20].pop("UIRoot")
    assert not native_selecting_hand_ready(decoder, root)
    tables[20]["UIRoot"] = _table(21)

    tables[30].pop("use_card")
    assert not native_selecting_hand_ready(decoder, root)


def test_round_eval_readiness_requires_cash_out_callback():
    decoder, root, tables = _native_fixture()

    assert native_round_eval_ready(decoder, root)

    tables[30].pop("cash_out")
    assert not native_round_eval_ready(decoder, root)


def test_pack_readiness_requires_open_pack_hand_and_callbacks():
    decoder, root, tables = _native_fixture()

    assert native_pack_ready(decoder, root)

    tables[40]["REMOVED"] = _boolean(True)
    assert not native_pack_ready(decoder, root)
    tables[40]["REMOVED"] = _boolean(False)

    tables[10].pop("cards")
    assert not native_pack_ready(decoder, root)
    tables[10]["cards"] = _table(11)

    tables[30].pop("skip_booster")
    assert not native_pack_ready(decoder, root)


class _RoutingObserver(SupervisorLiveMemoryBalatroObserver):
    def __init__(self, phase: str):
        self.snapshot = LiveBalatroSnapshot(
            sequence=1,
            phase=phase,
            state_complete=True,
        )
        self.readiness_calls = []
        self._last_exposed_phase = None
        self.blind_select_readiness_timeout_seconds = 1.0
        self.blind_select_readiness_poll_seconds = 0.0
        self.shop_readiness_timeout_seconds = 1.0
        self.shop_readiness_poll_seconds = 0.0

    def _observe_public(self):
        return self.snapshot

    def _wait_for_native_readiness(self, snapshot, **kwargs):
        self.readiness_calls.append((kwargs["phase"], kwargs["ready"]))
        return snapshot

    def _wait_for_full_state_quiet(self, snapshot):
        return snapshot


@pytest.mark.parametrize(
    ("phase", "ready"),
    (
        ("SELECTING_HAND", native_selecting_hand_ready),
        ("ROUND_EVAL", native_round_eval_ready),
        ("TAROT_PACK", native_pack_ready),
        ("PLANET_PACK", native_pack_ready),
        ("SPECTRAL_PACK", native_pack_ready),
        ("STANDARD_PACK", native_pack_ready),
        ("BUFFOON_PACK", native_pack_ready),
    ),
)
def test_supervisor_routes_remaining_action_phases_through_native_readiness(
    phase,
    ready,
):
    observer = _RoutingObserver(phase)

    result = observer.observe()

    assert result is observer.snapshot
    assert observer.readiness_calls == [(phase, ready)]
