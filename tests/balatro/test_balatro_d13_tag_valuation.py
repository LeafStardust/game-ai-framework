from __future__ import annotations

from types import SimpleNamespace

import pytest

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND
from games.balatro.blind_skip_policy import (
    CONSERVATIVE_TAG_VALUES,
    decide_blind_play_or_skip,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.external.live_memory_observer import (
    snapshot_payload_from_live_memory,
)
from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.protocol import LiveBalatroSnapshot


REQUIRED_TAG_KEYS = {
    "tag_uncommon",
    "tag_rare",
    "tag_negative",
    "tag_foil",
    "tag_holo",
    "tag_polychrome",
    "tag_investment",
    "tag_voucher",
    "tag_boss",
    "tag_standard",
    "tag_charm",
    "tag_meteor",
    "tag_buffoon",
    "tag_handy",
    "tag_garbage",
    "tag_ethereal",
    "tag_coupon",
    "tag_double",
    "tag_juggle",
    "tag_d_six",
    "tag_top_up",
    "tag_skip",
    "tag_orbital",
    "tag_economy",
}


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables.get(address, {})

    def array_items(self, address):
        return ()


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _number(value):
    return LuaValue("number", float(value), 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def _snapshot(
    tag: str | None,
    *,
    money: int = 10,
    blind_type: str = "SMALL",
    jokers: dict | None = None,
) -> LiveBalatroSnapshot:
    blind = {"type": blind_type, "status": "SELECT"}
    if tag is not None:
        blind["tag"] = tag
    payload = {"money": money, "blind": blind}
    if jokers is not None:
        payload["jokers"] = jokers
    return LiveBalatroSnapshot(
        sequence=1,
        phase="BLIND_SELECT",
        state_complete=True,
        payload=payload,
    )


def test_d13_classifies_every_normal_skip_tag():
    assert set(CONSERVATIVE_TAG_VALUES) == REQUIRED_TAG_KEYS


def test_live_memory_observer_exposes_current_public_blind_tag():
    game = 100
    states = 101
    round_resets = 102
    blind_tags = 103
    blind = 104
    tables = {
        game: {
            "dollars": _integer(10),
            "stake": _integer(1),
            "round_resets": _table(round_resets),
            "blind": _table(blind),
            "blind_on_deck": _string("Small"),
            "facing_blind": _boolean(False),
        },
        states: {"BLIND_SELECT": _number(1)},
        round_resets: {
            "ante": _integer(1),
            "blind_tags": _table(blind_tags),
        },
        blind_tags: {
            "Small": _string("tag_economy"),
            "Big": _string("tag_rare"),
        },
        blind: {
            "chips": _integer(300),
            "name": _string("Small Blind"),
            "boss": _boolean(False),
        },
    }
    decoder = _FakeDecoder(tables)
    root = {
        "GAME": _table(game),
        "STATE": _number(1),
        "STATE_COMPLETE": _boolean(True),
        "STATES": _table(states),
    }

    payload, phase, state_complete = snapshot_payload_from_live_memory(decoder, root)

    assert phase == "BLIND_SELECT"
    assert state_complete is True
    assert payload["blind"]["type"] == "SMALL"
    assert payload["blind"]["tag"] == "tag_economy"
    assert payload["hidden_rng_exposed"] is False
    assert payload["hidden_draw_order_exposed"] is False


def test_d13_economy_tag_uses_observed_public_cash_and_can_skip():
    decision = decide_blind_play_or_skip(_snapshot("tag_economy", money=10))

    assert decision.action_name == SKIP_BLIND
    assert decision.tag_key == "tag_economy"
    assert decision.tag_ev == pytest.approx(10.0)
    assert decision.tag_value_source == "observed_live_tag:tag_economy"
    assert "tag_key=tag_economy" in decision.notes


def test_d13_top_up_tag_respects_observed_joker_capacity():
    full = decide_blind_play_or_skip(
        _snapshot("tag_top_up", jokers={"count": 5, "limit": 5})
    )
    two_open = decide_blind_play_or_skip(
        _snapshot("tag_top_up", jokers={"count": 3, "limit": 5})
    )

    assert full.tag_ev == pytest.approx(0.0)
    assert full.action_name == SELECT_BLIND
    assert two_open.tag_ev == pytest.approx(5.0)
    assert two_open.tag_value_source == "observed_live_tag:tag_top_up"


def test_d13_unknown_observed_tag_fails_back_without_fabricating_value():
    decision = decide_blind_play_or_skip(
        _snapshot("tag_future"),
        fallback_tag_value=4.5,
    )

    assert decision.tag_key == "tag_future"
    assert decision.tag_ev == pytest.approx(4.5)
    assert decision.tag_value_source == "fallback_unmodeled_live_tag:tag_future"


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Translator:
    def translate(self, snapshot):
        return SimpleNamespace(phase=snapshot.phase, hand=[])


def test_autonomous_d13_consumes_observed_tag_specific_value():
    snapshot = _snapshot("tag_economy", money=10)
    runner = LiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(),
        bridge=object(),
        dispatcher=object(),
    )

    decision = runner.decide()

    assert decision.action.name == SKIP_BLIND
    assert decision.source == "D13 blind play-vs-skip policy"
    assert "tag_key=tag_economy" in decision.notes
    assert "tag_value_source=observed_live_tag:tag_economy" in decision.notes
