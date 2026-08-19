from types import SimpleNamespace

from games.balatro.actions import BUY_VOUCHER, END_SHOP, REFRESH_SHOP
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.external.live_memory_shop_terms import LiveShopRerollTerms
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import LiveShopItem
from games.balatro.state import BalatroState


class FakeObserver:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class FakeTranslator:
    def __init__(self, state):
        self.state = state

    def translate(self, snapshot):
        return self.state


def _snapshot() -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={"money": 20},
    )


def _state(*, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    return state


def _runner(state, terms_reader):
    return LiveMemoryInjectedSingleStepRunner(
        FakeObserver(_snapshot()),
        translator=FakeTranslator(state),
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
        reroll_terms_reader=terms_reader,
    )


def test_autonomous_shop_can_choose_observed_paid_reroll():
    runner = _runner(
        _state(money=20),
        lambda: LiveShopRerollTerms(cost=1.0, free_rerolls=0),
    )

    decision = runner.decide()

    assert decision.action.name == REFRESH_SHOP
    assert "shop_decision=REROLL" in decision.notes
    assert "observed_reroll_cost=1" in decision.notes
    assert "effective_reroll_spend=1" in decision.notes


def test_autonomous_shop_treats_free_reroll_as_zero_spend():
    runner = _runner(
        _state(money=0),
        lambda: LiveShopRerollTerms(cost=7.0, free_rerolls=1),
    )

    decision = runner.decide()

    assert decision.action.name == REFRESH_SHOP
    assert "free_rerolls=1" in decision.notes
    assert "effective_reroll_spend=0" in decision.notes


def test_autonomous_shop_keeps_strong_visible_offer_over_reroll():
    state = _state(money=20)
    state.shop_vouchers = [
        LiveShopItem(
            kind="VOUCHER",
            label="Antimatter",
            price=0,
            area_index=0,
        )
    ]
    runner = _runner(
        state,
        lambda: LiveShopRerollTerms(cost=1.0, free_rerolls=0),
    )

    decision = runner.decide()

    assert decision.action.name == BUY_VOUCHER
    assert "shop_decision=HOLD_REROLL" in decision.notes


def test_autonomous_shop_fails_closed_when_reroll_terms_are_unavailable():
    def unavailable():
        raise RuntimeError("reroll cost missing")

    runner = _runner(_state(money=20), unavailable)

    decision = runner.decide()

    assert decision.action.name == END_SHOP
    assert "shop_decision=HOLD_REROLL" in decision.notes
    assert any(
        note.startswith("reroll_terms_unavailable=reroll cost missing")
        for note in decision.notes
    )
