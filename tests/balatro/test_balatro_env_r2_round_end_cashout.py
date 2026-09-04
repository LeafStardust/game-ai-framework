import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_pristine_round_start
from games.balatro.env.round_end import (
    baseline_interest_dollars,
    cash_out_baseline_ordinary_blind,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
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

    # $14 pre-payout -> $2 interest. Reward is $3 and two unused hands add $2.
    # Using post-reward money for interest would produce a different result.
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


def test_env_r2_cashout_isolates_input_state_and_rng():
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
    assert result.rng_snapshot() == before_rng


def test_env_r2_cashout_supports_big_blind_baseline_too():
    result = cash_out_baseline_ordinary_blind(
        _cleared_run(blind_type=BlindType.BIG, reward=4, money=9, hands_remaining=1)
    )

    # $9 -> $1 baseline interest + $4 blind + $1 unused hand.
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
    run.public.discards_remaining = 2
    run.public.jokers.extend(
        [GoldenJoker(), Cloud9Joker(), DelayedGratificationJoker()]
    )

    result = cash_out_baseline_ordinary_blind(run)

    # Vanilla ordering: $24 pre-payout gives exactly $4 interest.  Joker rows are
    # Golden +$4, Cloud 9 +$4 for the four nines in a base deck, and Delayed
    # Gratification +$4 for two unused discards.  They do not inflate interest.
    assert result.public.money == 39
    assert result.public.discards_remaining == 2


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
    run.public.vouchers.append("Seed Money")
    with pytest.raises(HeadlessTransitionError, match="Voucher economy"):
        cash_out_baseline_ordinary_blind(run)

    # Burglar is exact at setting_blind but remains a separately classified
    # lifecycle acquisition; do not infer round-end admissibility from that.
    from games.balatro.jokers.burglar import BurglarJoker

    run = _cleared_run()
    run.public.jokers.append(BurglarJoker())
    with pytest.raises(HeadlessTransitionError, match="end-of-round Joker"):
        cash_out_baseline_ordinary_blind(run)


def test_env_r2_cashout_rejects_negative_money_and_preexisting_shop_contents():
    run = _cleared_run(money=-1)
    with pytest.raises(HeadlessTransitionError, match="negative-money"):
        cash_out_baseline_ordinary_blind(run)

    run = _cleared_run()
    run.public.shop_vouchers.append(object())
    with pytest.raises(HeadlessTransitionError, match="ungenerated shop"):
        cash_out_baseline_ordinary_blind(run)
