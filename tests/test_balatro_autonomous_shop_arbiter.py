from types import SimpleNamespace

from games.balatro.actions import BUY_BOOSTER, END_SHOP
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


def _runner(state, *, reroll_cost: float):
    return LiveMemoryInjectedSingleStepRunner(
        FakeObserver(_snapshot()),
        translator=FakeTranslator(state),
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
        reroll_terms_reader=lambda: LiveShopRerollTerms(
            cost=reroll_cost,
            free_rerolls=0,
        ),
    )


def test_autonomous_shop_can_buy_visible_celestial_pack_over_reroll():
    state = _state(money=20)
    state.shop_boosters = [
        LiveShopItem(
            kind="BOOSTER",
            label="Celestial Pack",
            price=4,
            area_index=0,
        )
    ]
    runner = _runner(state, reroll_cost=1.0)

    decision = runner.decide()

    assert decision.action.name == BUY_BOOSTER
    assert decision.action.target is state.shop_boosters[0]
    assert "shop_decision=HOLD_REROLL" in decision.notes
    assert "arbiter_source=BOOSTER" in decision.notes
    assert any(
        note == "unopened booster contents are not predicted"
        for note in decision.notes
    )


def test_autonomous_shop_does_not_open_unsafe_arcana_pack():
    state = _state(money=20)
    state.shop_boosters = [
        LiveShopItem(
            kind="BOOSTER",
            label="Arcana Pack",
            price=4,
            area_index=0,
        )
    ]
    runner = _runner(state, reroll_cost=10.0)

    decision = runner.decide()

    assert decision.action.name == END_SHOP
    assert decision.action.name != BUY_BOOSTER
    assert "shop_decision=HOLD_REROLL" in decision.notes
    assert "arbiter_source=END_SHOP" in decision.notes
