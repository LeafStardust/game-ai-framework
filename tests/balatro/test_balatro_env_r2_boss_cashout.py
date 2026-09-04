import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_cash_out import cash_out_supported_boss
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _boss_round(name: str, *, money: int = 14, reward: int = 5) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.money = money
    state.hand_size = 8
    state.boss_name = name
    state.blind_is_boss = True
    state.blind = Blind(BlindType.BOSS, requirement=100, reward=reward)
    state.blind_score = 100
    return HeadlessRunState(public=state, seed="BOSSCASH")


def _finish(run: HeadlessRunState, *, score: int = 120, hands: int = 1) -> HeadlessRunState:
    dealt = deal_supported_round_start(run)
    dealt.public.phase = "ROUND_EVAL"
    dealt.public.score = score
    dealt.public.hands_remaining = hands
    return dealt


def test_env_r2_simple_boss_cashout_pays_and_enters_ungenerated_shop():
    run = _finish(_boss_round("The Psychic", money=14, reward=5), hands=1)

    result = cash_out_supported_boss(run)

    # $14 + $5 Boss reward + $1 unused hand + $2 pre-payout interest.
    assert result.public.money == 22
    assert result.public.phase == "SHOP"
    assert result.public.shop_active is True
    assert result.public.shop_jokers == []
    assert result.public.shop_consumables == []
    assert result.public.shop_boosters == []
    assert result.public.shop_vouchers == []
    # Ante progression is owned by leaving the shop, not cash-out.
    assert result.public.ante == 1


def test_env_r2_manacle_boss_cashout_restores_persistent_hand_size_without_draw():
    run = _boss_round("The Manacle", money=9, reward=5)
    run.public.hand_size = 7
    run.boss_hand_size_sub = 1
    run = _finish(run, hands=0)
    assert len(run.public.hand) == 7

    result = cash_out_supported_boss(run)

    assert result.public.hand_size == 8
    assert result.boss_hand_size_sub is None
    assert result.public.hand == []
    assert len(result.draw_pile) == 52
    # $9 + $5 reward + $1 interest.
    assert result.public.money == 15


def test_env_r2_static_suit_boss_cashout_clears_debuffs_before_repopulation():
    run = _boss_round("The Goad", money=4, reward=5)
    for card in run.public.deck:
        card.debuffed = card.suit == "Spades"
    run = _finish(run, hands=0)
    assert sum(card.debuffed for card in run.require_playing_card_order()) == 13

    result = cash_out_supported_boss(run)

    assert all(not card.debuffed for card in result.require_playing_card_order())
    assert result.public.money == 9
    assert len(result.draw_pile) == 52


def test_env_r2_boss_cashout_preserves_pre_payout_interest_with_supported_joker_dollars():
    from games.balatro.jokers.golden_joker import GoldenJoker

    run = _finish(_boss_round("The Eye", money=24, reward=5), hands=0)
    run.public.jokers.append(GoldenJoker())
    run.public.boss_blind_state_observed = True
    run.public.boss_blind_hands = {"PAIR"}

    result = cash_out_supported_boss(run)

    # $24 + $5 Boss + $4 Golden + $4 interest. Golden does not raise interest.
    assert result.public.money == 37
    assert result.public.boss_blind_state_observed is False
    assert result.public.boss_blind_hands == set()


def test_env_r2_boss_cashout_isolates_input_and_rejects_unsupported_cleanup():
    run = _finish(_boss_round("The Psychic"))
    before_money = run.public.money
    before_hand = list(run.public.hand)
    before_rng = run.rng_snapshot()

    result = cash_out_supported_boss(run)

    assert result is not run
    assert run.public.money == before_money
    assert run.public.phase == "ROUND_EVAL"
    assert run.public.hand == before_hand
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() == before_rng

    unsupported = _finish(_boss_round("Amber Acorn"))
    with pytest.raises(HeadlessTransitionError, match="not exactly owned"):
        cash_out_supported_boss(unsupported)


def test_env_r2_boss_cashout_rejects_uncleared_or_nonboss_boundary():
    run = _finish(_boss_round("The Psychic"), score=99)
    with pytest.raises(HeadlessTransitionError, match="uncleared"):
        cash_out_supported_boss(run)

    run = _finish(_boss_round("The Psychic"))
    run.public.blind.type = BlindType.BIG
    with pytest.raises(HeadlessTransitionError, match="Boss Blind"):
        cash_out_supported_boss(run)
