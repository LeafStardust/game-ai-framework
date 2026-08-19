from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_BOOSTER, BUY_VOUCHER, END_SHOP, BalatroAction
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_sale_policy import JokerSalePolicy, JokerSaleThresholds
from games.balatro.live.shop import LiveShopItem
from games.balatro.playbook_shop_policy import PlaybookVoucherAwareBalatroShopPolicy
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    FutureShopOfferPrior,
    ShopRerollPoolPrior,
)
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy
from games.balatro.state import BalatroState


class _InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class _EmptyProfile:
    effects = ()

    def supports(self, feature):
        return False


class _StaticProfiler:
    def profile(self, state):
        return _EmptyProfile()


def _state(*, money: int) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def _voucher(label: str, *, price: int = 5) -> LiveShopItem:
    return LiveShopItem(kind="VOUCHER", label=label, price=price, area_index=0)


def _booster(*, price: int = 5) -> BalatroAction:
    return BalatroAction(
        BUY_BOOSTER,
        target=LiveShopItem(
            kind="BOOSTER",
            label="Celestial Pack",
            price=price,
            area_index=0,
        ),
    )


def test_d3_owned_seed_money_extends_interest_breakpoint():
    base = _state(money=50)
    seeded = _state(money=50)
    seeded.vouchers = ["Seed Money"]
    policy = VoucherAcquisitionPolicy()

    base_result = policy.decide(base, _voucher("Antimatter"))
    seeded_result = policy.decide(seeded, _voucher("Antimatter"))

    assert base_result.interest_penalty == pytest.approx(0.0)
    assert seeded_result.interest_penalty == pytest.approx(1.0)


def test_d8_owned_seed_money_extends_interest_breakpoint():
    base = _state(money=50)
    seeded = _state(money=50)
    seeded.vouchers = [SimpleNamespace(label="Seed Money")]
    policy = BuildAwareShopBoosterPolicy()

    base_result = policy.recommend(base, _booster())
    seeded_result = policy.recommend(seeded, _booster())

    assert base_result.interest_penalty == pytest.approx(0.0)
    assert seeded_result.interest_penalty == pytest.approx(1.25)


def test_d11_owned_seed_money_extends_reroll_interest_breakpoint():
    prior = ShopRerollPoolPrior(
        card_slots=1,
        offers=(
            FutureShopOfferPrior(
                family="TEST",
                weight=1.0,
                gross_utility=10.0,
                expected_price=0,
                resource="JOKER",
            ),
        ),
    )
    policy = BuildAwareShopRerollPolicy(
        shop_policy=BalatroShopPolicy(),
        build_profiler=_StaticProfiler(),
        pool_prior=prior,
    )
    base = _state(money=50)
    seeded = _state(money=50)
    seeded.vouchers = ["Seed Money"]

    base_result = policy.recommend(
        base,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    seeded_result = policy.recommend(
        seeded,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert seeded_result.reroll_resource_cost - base_result.reroll_resource_cost == pytest.approx(1.25)
    assert any("reroll interest penalty=1.250" in note for note in seeded_result.rationale)


def test_d2_sale_credit_uses_owned_seed_money_interest_cap():
    thresholds = JokerSaleThresholds(
        minimum_sale_advantage=0.0,
        maximum_build_loss=0.0,
        minimum_sell_credit=0,
        sell_credit_weight=0.0,
        interest_gain_weight=1.0,
        reserve_recovery_weight=0.0,
        full_slot_release_value=0.0,
    )
    joker = _InertJoker()
    joker.sell_cost = 5
    base = _state(money=45)
    base.joker_slots = 2
    base.jokers = [joker]
    seeded = _state(money=45)
    seeded.joker_slots = 2
    seeded.jokers = [joker]
    seeded.vouchers = ["Seed Money"]
    policy = JokerSalePolicy(thresholds)

    base_result = policy.decide(base)
    seeded_result = policy.decide(seeded)

    assert base_result.options[0].interest_gain == pytest.approx(0.0)
    assert seeded_result.options[0].interest_gain == pytest.approx(1.0)


def test_d14_voucher_remap_uses_owned_seed_money_interest_cap():
    base = _state(money=50)
    seeded = _state(money=50)
    seeded.vouchers = ["Seed Money"]
    action = BalatroAction(BUY_VOUCHER, target=_voucher("Antimatter"))
    policy = PlaybookVoucherAwareBalatroShopPolicy()

    base_score = policy.rank_actions(base, [action])[0]
    seeded_score = policy.rank_actions(seeded, [action])[0]

    assert base_score.interest_penalty == pytest.approx(0.0)
    assert seeded_score.interest_penalty == pytest.approx(1.25)
