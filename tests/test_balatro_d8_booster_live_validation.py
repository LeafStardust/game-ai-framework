import pytest

from games.balatro.live.external.live_memory_booster_policy_validation import (
    _execution_guard_errors,
    _state_fingerprint,
    build_live_d8_view,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import LiveShopItem
from games.balatro.shop_booster_policy import BUY, HOLD, BuildAwareShopBoosterPolicy
from games.balatro.state import BalatroState


def _snapshot(*, phase: str = "SHOP") -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=1,
        phase=phase,
        state_complete=True,
        payload={"money": 20},
    )


def _state(*, phase: str = "SHOP", money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = phase
    state.money = money
    state.shop_boosters = [
        LiveShopItem(
            kind="BOOSTER",
            label="Celestial Pack",
            price=4,
            live_id=123,
            area_index=0,
        )
    ]
    return state


def test_d8_live_view_recommends_affordable_celestial_buy():
    state = _state()
    view = build_live_d8_view(
        _snapshot(),
        state,
        policy=BuildAwareShopBoosterPolicy(),
    )

    assert len(view.candidates) == 1
    assert view.candidates[0].recommendation.decision == BUY
    assert view.recommendation is view.candidates[0]


def test_d8_live_guard_requires_exact_current_top_buy():
    state = _state()
    view = build_live_d8_view(
        _snapshot(),
        state,
        policy=BuildAwareShopBoosterPolicy(),
    )

    assert _execution_guard_errors(
        view,
        expect_booster="Celestial Pack",
        expect_index=0,
        expect_decision=BUY,
    ) == ()

    mismatch = _execution_guard_errors(
        view,
        expect_booster="Jumbo Celestial Pack",
        expect_index=0,
        expect_decision=BUY,
    )
    assert any("expected booster" in error for error in mismatch)

    hold = _execution_guard_errors(
        view,
        expect_booster="Celestial Pack",
        expect_index=0,
        expect_decision=HOLD,
    )
    assert any("only executes an expected BUY" in error for error in hold)


def test_d8_fingerprint_changes_on_money_or_booster_identity():
    state = _state()
    baseline = _state_fingerprint(state)

    money_changed = _state()
    money_changed.money = 19
    assert _state_fingerprint(money_changed) != baseline

    booster_changed = _state()
    booster_changed.shop_boosters[0].live_id = 999
    assert _state_fingerprint(booster_changed) != baseline


def test_d8_live_view_rejects_non_shop_phase():
    state = _state(phase="SELECTING_HAND")
    with pytest.raises(ValueError, match="requires SHOP phase"):
        build_live_d8_view(
            _snapshot(phase="SELECTING_HAND"),
            state,
            policy=BuildAwareShopBoosterPolicy(),
        )
