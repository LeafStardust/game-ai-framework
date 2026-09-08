import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _play_run(*, seed="R4-PLAY", requirement=9999, hands_remaining=4):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.blind = Blind(BlindType.SMALL, requirement)
    state.hands_remaining = hands_remaining
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


def _card_signature(card):
    return (card.rank, card.suit)


def test_env_r4_ordinary_play_high_card_updates_score_history_zones_and_redraws():
    run = _play_run()
    selected = run.public.hand[0]
    selected_signature = _card_signature(selected)
    expected_score = 5 + BalatroScorer.RANK_CHIPS[selected.rank]
    rng_before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == expected_score
    assert result.public.hands_remaining == 3
    assert result.public.hand_play_counts["HIGH_CARD"] == 1
    assert result.public.round_hand_play_counts["HIGH_CARD"] == 1
    assert result.public.last_played_hand == "HIGH_CARD"
    assert "HIGH_CARD" in result.public.visible_poker_hands
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert len(result.public.deck) == 43
    assert len(result.draw_pile) == 43
    assert result.played_pile == []
    assert _card_signature(result.public.discard_pile[-1]) == selected_signature
    assert _card_signature(result.discard_pile[-1]) == selected_signature
    assert result.public.discard_pile[-1].played_this_ante is True
    assert result.public.discard_pile[-1].played_this_ante_observed is True
    assert result.rng_snapshot() == rng_before

    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.public.hand_play_counts["HIGH_CARD"] == 0
    assert run.public.round_hand_play_counts["HIGH_CARD"] == 0
    assert run.public.discard_pile == []
    assert run.discard_pile == []
    assert selected.played_this_ante is False
    assert selected.played_this_ante_observed is False


def test_env_r4_ordinary_play_recognizes_and_scores_pair_exactly():
    run = None
    indices = None
    for attempt in range(100):
        candidate = _play_run(seed=f"R4-PAIR-{attempt}")
        by_rank = {}
        for index, card in enumerate(candidate.public.hand):
            by_rank.setdefault(card.rank, []).append(index)
        pair = next((values[:2] for values in by_rank.values() if len(values) >= 2), None)
        if pair is not None:
            run = candidate
            indices = tuple(pair)
            break

    assert run is not None and indices is not None
    cards = [run.public.hand[index] for index in indices]
    expected_score = (
        10 + sum(BalatroScorer.RANK_CHIPS[card.rank] for card in cards)
    ) * 2

    result = apply_supported_ordinary_play(run, reversed(indices))

    assert result.public.score == expected_score
    assert result.public.hand_play_counts["PAIR"] == 1
    assert result.public.round_hand_play_counts["PAIR"] == 1
    assert result.public.last_played_hand == "PAIR"
    assert "PAIR" in result.public.visible_poker_hands


def test_env_r4_ordinary_play_clear_stops_at_pre_cashout_round_eval_without_redraw():
    run = _play_run(requirement=1)
    selected_signature = _card_signature(run.public.hand[0])
    rng_before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.phase == "ROUND_EVAL"
    assert result.public.score >= result.public.blind.requirement
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == 7
    assert len(result.public.deck) == 44
    assert len(result.draw_pile) == 44
    assert _card_signature(result.public.discard_pile[-1]) == selected_signature
    assert result.played_pile == []
    assert result.rng_snapshot() == rng_before


def test_env_r4_ordinary_play_final_hand_failure_enters_game_over_without_redraw():
    run = _play_run(requirement=9999, hands_remaining=1)
    selected_signature = _card_signature(run.public.hand[0])

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.phase == "GAME_OVER"
    assert result.public.score < result.public.blind.requirement
    assert result.public.hands_remaining == 0
    assert len(result.public.hand) == 7
    assert len(result.public.deck) == 44
    assert _card_signature(result.public.discard_pile[-1]) == selected_signature
    assert result.played_pile == []


@pytest.mark.parametrize(
    "field, value",
    [
        ("enhancement", "Lucky"),
        ("edition", "Foil"),
        ("seal", "Red"),
        ("permanent_bonus", 1),
        ("debuffed", True),
        ("forced_selection", True),
        ("face_down", True),
    ],
)
def test_env_r4_ordinary_play_fails_closed_on_unowned_card_effects(field, value):
    run = _play_run()
    setattr(run.public.hand[0], field, value)

    with pytest.raises(
        HeadlessTransitionError,
        match="modified/debuffed/forced/face-down card effects",
    ):
        apply_supported_ordinary_play(run, (0,))


def test_env_r4_ordinary_play_fails_closed_on_joker_tag_consumable_and_voucher_callbacks():
    joker_run = _play_run(seed="R4-JOKER")
    joker_run.public.jokers = [object()]
    with pytest.raises(HeadlessTransitionError, match="Joker callbacks"):
        apply_supported_ordinary_play(joker_run, (0,))

    tag_run = _play_run(seed="R4-TAG")
    tag_run.tags.append("tag_double")
    with pytest.raises(HeadlessTransitionError, match="Tag callbacks"):
        apply_supported_ordinary_play(tag_run, (0,))

    consumable_run = _play_run(seed="R4-CONSUMABLE")
    consumable_run.public.consumables = [object()]
    with pytest.raises(HeadlessTransitionError, match="held consumable"):
        apply_supported_ordinary_play(consumable_run, (0,))

    voucher_run = _play_run(seed="R4-VOUCHER")
    voucher_run.public.vouchers = ["v_observatory"]
    with pytest.raises(HeadlessTransitionError, match="Voucher action-time"):
        apply_supported_ordinary_play(voucher_run, (0,))


def test_env_r4_ordinary_play_rejects_invalid_selection_and_stale_private_zone():
    run = _play_run()
    with pytest.raises(HeadlessTransitionError, match="distinct"):
        apply_supported_ordinary_play(run, (0, 0))

    stale = _play_run(seed="R4-STALE")
    stale.draw_pile.pop()
    with pytest.raises(HeadlessTransitionError, match="private/public draw zones"):
        apply_supported_ordinary_play(stale, (0,))
