import pytest
from types import SimpleNamespace

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    END_SHOP,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import (
    BUY,
    JokerAcquisitionDecision,
    JokerAcquisitionOption,
    JokerAcquisitionThresholds,
    JokerTransactionEconomics,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.external.live_memory_shop_terms import LiveShopRerollTerms
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import LiveShopItem
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_policy import ShopActionScore
from games.balatro.shop_reroll_policy import ShopRerollRecommendation
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


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class StaticShopPolicy:
    hold_bias = 0.35

    def __init__(self, deterministic_total: float):
        self.deterministic_total = float(deterministic_total)

    def rank_actions(self, state, actions):
        return [
            ShopActionScore(action=action, total=self.deterministic_total)
            for action in actions
        ]


class StaticJokerPolicy:
    def __init__(self, total_advantage: float):
        self.total_advantage = float(total_advantage)

    def decide(self, state, candidate):
        economics = JokerTransactionEconomics(
            price=0,
            sell_credit=0,
            net_spend=0,
            money_after=int(state.money),
            edition_delta=0.0,
            price_penalty=0.0,
            interest_penalty=0.0,
            reserve_penalty=0.0,
            slot_penalty=0.0,
        )
        option = JokerAcquisitionOption(
            mode=BUY,
            build_gain=self.total_advantage,
            total_advantage=self.total_advantage,
            economics=economics,
            eligible=True,
        )
        return JokerAcquisitionDecision(
            action=BUY,
            candidate=type(candidate).__name__,
            selected=option,
            options=(option,),
            thresholds=JokerAcquisitionThresholds(),
        )


class NoBoosterPolicy:
    def recommend(self, state, action):
        raise AssertionError("unexpected booster recommendation")


class CapturingRerollPolicy:
    def __init__(self):
        self.visible_score_floor = None

    def recommend(
        self,
        state,
        visible_actions,
        *,
        reroll_cost,
        visible_score_floor=None,
    ):
        self.visible_score_floor = visible_score_floor
        return ShopRerollRecommendation(
            decision="HOLD",
            reroll_cost=reroll_cost,
            executable_action=None,
            current_best_score=float(visible_score_floor or 0.0),
            future_shop_ev=0.0,
            reroll_resource_cost=0.0,
            reroll_score=float("-inf"),
        )


class FreeRerollPolicy:
    def recommend(
        self,
        state,
        visible_actions,
        *,
        reroll_cost,
        visible_score_floor=None,
    ):
        assert reroll_cost == 0
        score = float(visible_score_floor or 0.35)
        return ShopRerollRecommendation(
            decision="REROLL",
            reroll_cost=0,
            executable_action=BalatroAction(REFRESH_SHOP),
            current_best_score=score,
            future_shop_ev=score,
            reroll_resource_cost=0.0,
            reroll_score=score,
        )


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


def test_autonomous_shop_rerolls_over_single_hand_normal_celestial_pack():
    state = _state(money=20)
    # Repeated Flush play creates Planet headroom, but a normal Celestial pack still
    # has only a 3/12 chance to expose that one useful Planet.  D8 rejects the pack,
    # leaving the admitted reroll to win whole-shop arbitration.
    state.hand_levels["FLUSH"] = 2
    state.hand_play_counts["FLUSH"] = 8
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

    assert decision.action.name == REFRESH_SHOP
    assert "shop_decision=REROLL" in decision.notes
    assert "arbiter_source=REROLL" in decision.notes
    assert "admitted boosters=0/1" in decision.notes
    assert any(
        note == "future-shop expectation uses static public priors only; no RNG state or future ordering"
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


def test_shop_arbiter_compares_child_gain_over_each_no_action_baseline():
    state = _state(money=20)
    candidate = InertJoker()
    state.shop_jokers = [candidate]
    consumable = SimpleNamespace(price=0)
    reroll = CapturingRerollPolicy()
    arbiter = BuildAwareShopArbiter(
        shop_policy=StaticShopPolicy(deterministic_total=0.50),
        booster_policy=NoBoosterPolicy(),
        reroll_policy=reroll,
        joker_policy=StaticJokerPolicy(total_advantage=0.40),
    )

    decision = arbiter.decide(
        state,
        [
            BalatroAction(BUY_CONSUMABLE, target=consumable),
            BalatroAction(BUY_JOKER, target=candidate),
            BalatroAction(END_SHOP),
        ],
        reroll_cost=1,
    )

    assert decision.action.name == BUY_JOKER
    assert decision.source == "JOKER_BUY"
    assert decision.total == pytest.approx(0.40)
    assert decision.normalized_gain == pytest.approx(0.40)
    assert reroll.visible_score_floor == pytest.approx(0.75)


def test_shop_arbiter_uses_explicit_zero_gain_end_shop_baseline():
    state = _state(money=20)
    reroll = CapturingRerollPolicy()
    arbiter = BuildAwareShopArbiter(
        shop_policy=StaticShopPolicy(deterministic_total=0.20),
        booster_policy=NoBoosterPolicy(),
        reroll_policy=reroll,
        joker_policy=StaticJokerPolicy(total_advantage=0.0),
    )

    decision = arbiter.decide(
        state,
        [BalatroAction(BUY_CONSUMABLE, target=SimpleNamespace(price=0))],
        reroll_cost=1,
    )

    assert decision.action.name == END_SHOP
    assert decision.source == "END_SHOP"
    assert decision.total == pytest.approx(0.35)
    assert decision.normalized_gain == pytest.approx(0.0)
    assert reroll.visible_score_floor == pytest.approx(0.35)


def test_shop_arbiter_prefers_admitted_free_reroll_over_zero_gain_end_shop():
    state = _state(money=0)
    arbiter = BuildAwareShopArbiter(
        shop_policy=StaticShopPolicy(deterministic_total=0.20),
        booster_policy=NoBoosterPolicy(),
        reroll_policy=FreeRerollPolicy(),
        joker_policy=StaticJokerPolicy(total_advantage=0.0),
    )

    decision = arbiter.decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=0,
    )

    assert decision.action.name == REFRESH_SHOP
    assert decision.source == "REROLL"
    assert decision.total == pytest.approx(0.35)
    assert decision.normalized_gain == pytest.approx(0.0)
