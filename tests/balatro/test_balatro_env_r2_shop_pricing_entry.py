from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.round_end import cash_out_baseline_ordinary_blind
from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.shop_pricing import price_base_shop_joker_descriptor
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _cleared_small_blind() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "ROUND_EVAL"
    state.money = 10
    state.score = 300
    state.hands_remaining = 2
    state.blind = Blind(BlindType.SMALL, requirement=300, reward=3)
    state.owned_deck = list(state.deck)
    state.vouchers_observed = True
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    run = HeadlessRunState(public=state, seed="PRICE-ENTRY")
    run.draw_pile = list(state.deck)
    return run


def test_env_r2_baseline_cash_out_installs_authoritative_zero_pricing_state():
    result = cash_out_baseline_ordinary_blind(_cleared_small_blind())

    assert result.public.phase == "SHOP"
    assert result.public.shop_active is True
    assert result.public.shop_inflation_observed is True
    assert result.public.shop_inflation == 0
    assert result.public.shop_discount_percent_observed is True
    assert result.public.shop_discount_percent == 0


def test_env_r2_shop_entered_by_cash_out_can_price_generated_joker_descriptor():
    result = cash_out_baseline_ordinary_blind(_cleared_small_blind())
    descriptor = OrdinaryShopJokerDescriptor(
        run=result,
        center_key="j_joker",
        rarity=1,
        base_cost=5,
        edition="Foil",
        resamples=0,
    )

    assert price_base_shop_joker_descriptor(descriptor) == 7
