import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_pristine_round_start
from games.balatro.env.round_end import (
    baseline_interest_dollars,
    cash_out_baseline_ordinary_blind,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.to_the_moon import ToTheMoonJoker
from games.balatro.state import BalatroState


def _cleared_run(
    *,
    money: int = 14,
    hands_remaining: int = 2,
    blind_type: BlindType = BlindType.SMALL,
    reward: int = 3,
) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.hand_size = 8
    state.money = money
    state.blind = Blind(blind_type, requirement=100, reward=reward)
    state.blind_is_boss = blind_type is BlindType.BOSS
    state.vouchers_observed = True
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 4

    run = deal_pristine_round_start(HeadlessRunState(public=state, seed="CASHOUT"))
    run.public.phase = "ROUND_EVAL"
    run.public.score = 120
    run.public.hands_remaining = hands_remaining
    return run


def _ids(cards):
    return {id(card) for card in cards}


def test_env_r2_baseline_interest_uses_pre_payout_money_and_caps_at_five():
    assert baseline_interest_dollars(4) == 0
    assert baseline_interest_dollars(5) == 1
    assert baseline_interest_dollars(14) == 2
    assert baseline_interest_dollars(24) == 4
    assert baseline_interest_dollars(25) == 5
    assert baseline_interest_dollars(100) == 5


def test_env_r2_cashout_pays_blind_hands_and_interest_from_pre_payout_money():
    run = _cleared_run(money=14, hands_remaining=2, reward=3)
    result = cash_out_baseline_ordinary_blind(run)
    assert result.public.money == 21
    assert result.public.phase == "SHOP"
    assert result.public.shop_active is True


def test_env_r2_cashout_repopulates_all_permanent_cards_before_shop_entry():
    run = _cleared_run()
    assert len(run.public.hand) == 8
    assert len(run.draw_pile) == 44
    result = cash_out_baseline_ordinary_blind(run)
    assert result.public.hand == []
    assert result.public.discard_pile == []
    assert result.discard_pile == []
    assert result.played_pile == []
    assert len(result.draw_pile) == 52
    assert len(result.public.deck) == 52
    assert result.public.owned_deck is not None
    assert _ids(result.draw_pile) == _ids(result.public.owned_deck)
    assert _ids(result.public.deck) == _ids(result.public.owned_deck)


def test_env_r2_cashout_stops_before_shop_inventory_rng():
    result = cash_out_baseline_ordinary_blind(_cleared_run())
    assert result.public.shop_jokers == []
    assert result.public.shop_consumables == []
    assert result.public.shop_boosters == []
    assert result.public.shop_vouchers == []


def test_env_r2_cashout_isolates_input_and_consumes_exact_cashout_shuffle_rng():
    run = _cleared_run()
    before_money = run.public.money
    before_hand = list(run.public.hand)
    before_draw = list(run.draw_pile)
    before_rng = run.rng_snapshot()
    result = cash_out_baseline_ordinary_blind(run)
    assert result is not run
    assert run.public.money == before_money
    assert run.public.phase == "ROUND_EVAL"
    assert run.public.shop_active is False
    assert run.public.hand == before_hand
    assert run.draw_pile == before_draw
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() != before_rng
    assert "cashout1" in result.rng_snapshot()["nodes"]
    assert result.public.score == 0
    assert result.public.blind_score == 0
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 4
    assert result.public.blind.requirement == 0
    assert result.public.blind.reward == 0


def test_env_r2_cashout_supports_big_blind_baseline_too():
    result = cash_out_baseline_ordinary_blind(
        _cleared_run(blind_type=BlindType.BIG, reward=4, money=9, hands_remaining=1)
    )
    assert result.public.money == 15


def test_env_r2_cashout_accepts_audited_round_end_inert_scoring_jokers():
    from games.balatro.jokers.jolly_joker import JollyJoker
    from games.balatro.jokers.steel_joker import SteelJoker
    run = _cleared_run()
    run.public.jokers.extend([JollyJoker(), SteelJoker()])
    result = cash_out_baseline_ordinary_blind(run)
    assert result.public.money == 21
    assert [type(joker) for joker in result.public.jokers] == [JollyJoker, SteelJoker]


def test_env_r2_cashout_pays_exact_golden_cloud9_and_delayed_gratification_rows():
    from games.balatro.jokers.cloud_9 import Cloud9Joker
    from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
    from games.balatro.jokers.golden_joker import GoldenJoker
    run = _cleared_run(money=24, hands_remaining=0, reward=3)
    run.public.discards_used = 0
    run.public.discards_remaining = 2
    run.public.jokers.extend([GoldenJoker(), Cloud9Joker(), DelayedGratificationJoker()])
    result = cash_out_baseline_ordinary_blind(run)
    assert result.public.money == 43
    assert result.public.discards_remaining == 4


@pytest.mark.parametrize(("debuffed", "payout"), [(False, 3), (True, 0)])
def test_env_r2_cloud9_counts_permanent_nonstone_nines_and_respects_debuff(debuffed, payout):
    from games.balatro.jokers.cloud_9 import Cloud9Joker

    run = _cleared_run(money=14, hands_remaining=0, reward=3)
    nines = [card for card in run.public.owned_deck if card.rank == "9"]
    nines[0].enhancement = "Stone"
    nines[1].debuffed = True
    joker = Cloud9Joker()
    joker.debuffed = debuffed
    run.public.jokers = [joker]

    result = cash_out_baseline_ordinary_blind(run)

    assert result.public.money == 19 + payout
    assert run.public.money == 14


def test_env_r2_held_gold_round_end_pays_retriggers_before_interest():
    from games.balatro.jokers.mime import MimeJoker

    run = _cleared_run(money=4, hands_remaining=0, reward=3)
    run.public.hand[0].enhancement = "Gold"
    run.public.hand[0].seal = "Red"
    run.public.hand[1].enhancement = "Gold"
    run.public.hand[1].debuffed = True
    run.draw_pile[0].enhancement = "Gold"
    run.public.jokers = [MimeJoker()]

    result = cash_out_baseline_ordinary_blind(run)

    # The held active card pays three times. Interest uses $13, before the blind reward.
    assert result.public.money == 18
    assert run.public.money == 4
    assert sum(card.enhancement == "Gold" for card in result.public.owned_deck) == 3


def test_env_r2_cashout_pays_exact_materialized_generated_golden_joker():
    from games.balatro.env.shop_items import (
        GeneratedShopJokerItem,
        materialize_generated_shop_joker_for_acquisition,
    )
    from games.balatro.jokers.golden_joker import GoldenJoker

    run = _cleared_run(money=14, hands_remaining=0, reward=3)
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_golden", 1, 6, None, 6, False)
        )
    ]

    result = cash_out_baseline_ordinary_blind(run)

    assert run.public.money == 14
    assert result.public.money == 23
    assert type(result.public.jokers[0]) is GoldenJoker


def test_env_r2_cashout_treats_exact_materialized_generated_bull_as_inert():
    from games.balatro.env.shop_items import (
        GeneratedShopJokerItem,
        materialize_generated_shop_joker_for_acquisition,
    )
    from games.balatro.jokers.bull import BullJoker

    run = _cleared_run(money=14, hands_remaining=0, reward=3)
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_bull", 2, 6, None, 6, False)
        )
    ]

    result = cash_out_baseline_ordinary_blind(run)

    assert run.public.money == 14
    assert result.public.money == 19
    assert type(result.public.jokers[0]) is BullJoker


def test_env_r2_cashout_pays_rocket_current_value_without_mutating_input():
    from games.balatro.jokers.rocket import RocketJoker

    run = _cleared_run(money=14, hands_remaining=0, reward=3)
    run.public.jokers = [RocketJoker()]

    result = cash_out_baseline_ordinary_blind(run)

    assert run.public.money == 14
    assert run.public.jokers[0].dollars == 1
    assert result.public.money == 20
    assert result.public.jokers[0].dollars == 1
    assert result.public.jokers[0] is not run.public.jokers[0]


@pytest.mark.parametrize(("field", "value"), [("dollars", True), ("dollars", -1), ("increase", -1)])
def test_env_r2_cashout_rejects_malformed_rocket_payout_state(field, value):
    from games.balatro.jokers.rocket import RocketJoker

    run = _cleared_run()
    rocket = RocketJoker()
    setattr(rocket, field, value)
    run.public.jokers = [rocket]

    with pytest.raises(HeadlessTransitionError, match="Rocket"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_delayed_gratification_does_not_pay_after_any_discard_used():
    from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
    run = _cleared_run(money=14, hands_remaining=0, reward=3)
    run.public.discards_used = 1
    run.public.discards_remaining = 2
    run.public.jokers.append(DelayedGratificationJoker())
    result = cash_out_baseline_ordinary_blind(run)
    assert result.public.money == 19


def test_env_r2_cashout_delayed_gratification_requires_observed_discard_history():
    from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
    run = _cleared_run()
    run.public.discards_used = None
    run.public.discards_remaining = 2
    run.public.jokers.append(DelayedGratificationJoker())
    with pytest.raises(HeadlessTransitionError, match="discards_used must be an exact integer"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_cloud9_requires_authoritative_permanent_deck():
    from games.balatro.jokers.cloud_9 import Cloud9Joker
    run = _cleared_run()
    run.public.jokers.append(Cloud9Joker())
    run.public.owned_deck = None
    with pytest.raises(HeadlessTransitionError, match="Cloud 9.*owned_deck"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_delayed_gratification_requires_exact_nonnegative_discards():
    from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
    run = _cleared_run()
    run.public.jokers.append(DelayedGratificationJoker())
    run.public.discards_used = 0
    run.public.discards_remaining = -1
    with pytest.raises(HeadlessTransitionError, match="discards_remaining cannot be negative"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_rejects_uncleared_boss_or_wrong_phase():
    run = _cleared_run()
    run.public.score = 99
    with pytest.raises(HeadlessTransitionError, match="uncleared"):
        cash_out_baseline_ordinary_blind(run)
    run = _cleared_run()
    run.public.phase = "SELECTING_HAND"
    with pytest.raises(HeadlessTransitionError, match="ROUND_EVAL"):
        cash_out_baseline_ordinary_blind(run)
    run = _cleared_run(blind_type=BlindType.BOSS)
    with pytest.raises(HeadlessTransitionError, match="Small/Big"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_rejects_unowned_economy_and_lifecycle_modifiers():
    run = _cleared_run()
    run.tags.append("Economy")
    with pytest.raises(HeadlessTransitionError, match="tag cash-out"):
        cash_out_baseline_ordinary_blind(run)

    run = _cleared_run()
    # Magic Trick adds playing-card inventory to the main shop; that generation
    # and purchase lifecycle is still outside the currently exact shop boundary.
    run.public.vouchers.append("v_magic_trick")
    with pytest.raises(HeadlessTransitionError, match="Voucher"):
        cash_out_baseline_ordinary_blind(run)

    from games.balatro.jokers.burglar import BurglarJoker
    run = _cleared_run()
    run.public.jokers.append(BurglarJoker())
    with pytest.raises(HeadlessTransitionError, match="end-of-round Joker"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_rejects_preexisting_shop_contents():
    run = _cleared_run()
    run.public.shop_vouchers.append(object())
    with pytest.raises(HeadlessTransitionError, match="ungenerated shop"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_preserves_supported_voucher_state_into_next_shop():
    run = _cleared_run()
    run.public.vouchers = ["v_clearance_sale", "v_tarot_merchant", "v_reroll_surplus"]
    run.public.shop_discount_percent = 25
    run.public.tarot_rate = 9.6
    run.base_reroll_cost = 3
    run.reroll_cost = 4
    result = cash_out_baseline_ordinary_blind(run)
    assert result.public.vouchers == run.public.vouchers
    assert result.public.shop_discount_percent_observed is True
    assert result.public.shop_discount_percent == 25
    assert result.public.joker_generation_edition_rate == 1.0
    assert result.public.tarot_rate == 9.6
    assert result.public.planet_rate == 4.0
    assert result.base_reroll_cost == 3
    assert result.reroll_cost == 3


@pytest.mark.parametrize(("balance", "gold", "expected"), [
    (-10, False, -1),
    (4, False, 13),
    (2, True, 16),
])
def test_env_r2_moon_interest_counts_held_gold_before_payout_rows(balance, gold, expected):
    run = _cleared_run(money=balance)
    if gold:
        run.public.hand[0].enhancement = "Gold"
    run.public.jokers = [ToTheMoonJoker(), GoldenJoker()]

    result = cash_out_baseline_ordinary_blind(run)

    assert result.public.money == expected
    assert run.public.money == balance
