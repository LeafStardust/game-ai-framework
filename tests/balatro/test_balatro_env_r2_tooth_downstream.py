import pytest

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.boss_play import apply_tooth_press_play_economy
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _tooth_run(*, money: int = 10) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Tooth"
    state.money = money
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hands_remaining = 1
    state.discards_remaining = 1
    return HeadlessRunState(public=state, seed="TOOTH")


@pytest.mark.parametrize("played_count", [1, 3, 5])
def test_env_r2_tooth_loses_exactly_one_dollar_per_played_card(played_count):
    started = start_supported_start_inert_boss(_tooth_run(money=10))
    action = BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:played_count]))

    result = apply_tooth_press_play_economy(started, action)

    assert result.public.money == 10 - played_count
    assert started.public.money == 10


def test_env_r2_tooth_allows_negative_money_like_vanilla_ease_dollars():
    started = start_supported_start_inert_boss(_tooth_run(money=1))
    action = BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:5]))

    result = apply_tooth_press_play_economy(started, action)

    assert result.public.money == -4


def test_env_r2_tooth_press_play_preserves_rng_and_card_zones():
    started = start_supported_start_inert_boss(_tooth_run(money=10))
    before_rng = started.rng_snapshot()
    before_hand = list(started.public.hand)
    before_deck = list(started.public.deck)
    before_draw = list(started.draw_pile)

    result = apply_tooth_press_play_economy(
        started,
        BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:2])),
    )

    assert result.rng_snapshot() == before_rng
    assert started.rng_snapshot() == before_rng
    assert result.public.hand == before_hand
    assert result.public.deck == before_deck
    assert result.draw_pile == before_draw


def test_env_r2_tooth_rejects_nonplay_wrong_phase_and_non_tooth_boundary():
    started = start_supported_start_inert_boss(_tooth_run())

    with pytest.raises(HeadlessTransitionError, match="PLAY_CARDS"):
        apply_tooth_press_play_economy(
            started,
            BalatroAction(DISCARD_CARDS, cards=list(started.public.hand[:1])),
        )

    wrong_phase = started.copy()
    wrong_phase.public.phase = "SHOP"
    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        apply_tooth_press_play_economy(
            wrong_phase,
            BalatroAction(PLAY_CARDS, cards=list(wrong_phase.public.hand[:1])),
        )

    wrong_boss = started.copy()
    wrong_boss.public.boss_name = "The Flint"
    with pytest.raises(HeadlessTransitionError, match="The Tooth"):
        apply_tooth_press_play_economy(
            wrong_boss,
            BalatroAction(PLAY_CARDS, cards=list(wrong_boss.public.hand[:1])),
        )


def test_env_r2_tooth_requires_unique_authoritative_hand_objects():
    started = start_supported_start_inert_boss(_tooth_run())
    card = started.public.hand[0]

    with pytest.raises(HeadlessTransitionError, match="duplicate"):
        apply_tooth_press_play_economy(
            started,
            BalatroAction(PLAY_CARDS, cards=[card, card]),
        )

    copied_card = BalatroCard(
        card.rank,
        card.suit,
        enhancement=card.enhancement,
        edition=card.edition,
        seal=card.seal,
        live_id=card.live_id,
    )
    with pytest.raises(HeadlessTransitionError, match="authoritative current-hand"):
        apply_tooth_press_play_economy(
            started,
            BalatroAction(PLAY_CARDS, cards=[copied_card]),
        )

    with pytest.raises(HeadlessTransitionError, match="at least one"):
        apply_tooth_press_play_economy(started, BalatroAction(PLAY_CARDS, cards=[]))
