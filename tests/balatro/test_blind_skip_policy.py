import pytest

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND, BalatroAction
from games.balatro.blind_skip_policy import decide_blind_play_or_skip
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.install import bridge_asset_path
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(
    blind_type: str,
    *,
    sequence: int = 1,
    money: int = 10,
) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="BLIND_SELECT",
        state_complete=True,
        payload={
            "money": money,
            "blind": {"type": blind_type, "status": "SELECT"},
        },
    )


def test_default_unknown_tag_value_favors_playing_small_blind():
    decision = decide_blind_play_or_skip(_snapshot("SMALL"))

    assert decision.action_name == SELECT_BLIND
    assert decision.margin == pytest.approx(1.0)
    assert decision.threshold == pytest.approx(2.0)
    assert decision.tag_value_source == "fallback_unidentified_live_tag"


def test_high_fallback_tag_value_can_intentionally_skip():
    decision = decide_blind_play_or_skip(
        _snapshot("SMALL"),
        threshold=1.0,
        fallback_tag_value=6.0,
    )

    assert decision.action_name == SKIP_BLIND
    assert decision.play_ev == pytest.approx(3.0)
    assert decision.skip_ev == pytest.approx(6.0)
    assert decision.margin == pytest.approx(3.0)
    assert "blind_decision=SKIP" in decision.notes
    assert "tag_value_source=fallback_unidentified_live_tag" in decision.notes


def test_cash_poor_state_adds_skip_opportunity_cost():
    decision = decide_blind_play_or_skip(
        _snapshot("SMALL", money=0),
        threshold=1.0,
        fallback_tag_value=5.0,
    )

    assert decision.economy_opportunity_cost == pytest.approx(1.25)
    assert decision.skip_ev == pytest.approx(3.75)
    assert decision.margin == pytest.approx(0.75)
    assert decision.action_name == SELECT_BLIND


def test_boss_blind_is_never_skipped_even_with_extreme_tag_value():
    decision = decide_blind_play_or_skip(
        _snapshot("BOSS"),
        threshold=0.0,
        fallback_tag_value=100.0,
    )

    assert decision.action_name == SELECT_BLIND
    assert decision.blind_type == "BOSS"


class _Observer:
    def __init__(self, snapshots):
        self._snapshots = iter(snapshots)

    def observe(self):
        return next(self._snapshots)


class _Bridge:
    def __init__(self):
        self.skip_calls = 0

    def skip_blind(self):
        self.skip_calls += 1


def test_dispatcher_executes_skip_and_verifies_blind_advanced():
    before = _snapshot("SMALL", sequence=10)
    after = _snapshot("BIG", sequence=11)
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer([after]),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    result = dispatcher.dispatch(BalatroAction(SKIP_BLIND), snapshot=before)

    assert bridge.skip_calls == 1
    assert result.after == after
    assert result.details == {"blind_before": "SMALL", "blind_after": "BIG"}


def test_dispatcher_rejects_boss_skip_before_bridge_call():
    before = _snapshot("BOSS", sequence=10)
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer([]),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="Small/Big"):
        dispatcher.dispatch(BalatroAction(SKIP_BLIND), snapshot=before)

    assert bridge.skip_calls == 0


def test_lua_bridge_routes_skip_blind_to_native_callback():
    bridge_lua = bridge_asset_path().read_text(encoding="utf-8")

    assert 'action == "SKIP_BLIND"' in bridge_lua
    assert "G.FUNCS and G.FUNCS.skip_blind" in bridge_lua
    assert 'get_UIE_by_ID("tag_" .. current_blind)' in bridge_lua
