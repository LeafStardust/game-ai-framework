from itertools import combinations

import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    materialize_generated_shop_joker_for_acquisition,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState
from games.balatro.consumable import PlanetCard
from games.balatro.tarots import Fool


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


def test_env_r4_ordinary_play_flips_authoritative_stale_draw_facing_on_entry():
    run = _play_run(seed="R4-STALE-DRAW-FACING")
    stale = run.draw_pile[-1]
    stale.face_down = True
    stale.facing_observed = True
    before = serialize_headless_run_state(run)

    result = apply_supported_ordinary_play(run, (0,))

    drawn = next(
        card
        for card in result.public.hand
        if card.rank == stale.rank and card.suit == stale.suit
    )
    assert drawn.face_down is False
    assert drawn.facing_observed is True
    assert serialize_headless_run_state(run) == before


def test_env_r4_ordinary_play_rejects_unobserved_stale_draw_facing_atomically():
    run = _play_run(seed="R4-STALE-DRAW-UNOBSERVED")
    run.draw_pile[-1].face_down = True
    run.draw_pile[-1].facing_observed = False
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="face-down card effects"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before


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


def test_env_r4_selecting_blind_does_not_activate_its_skip_tag():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round = 0
    state.blind = Blind(BlindType.SMALL, 300, reward=3, tag_key="tag_double")
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 4
    run = HeadlessRunState(public=state, seed="R4-SKIP-TAG")

    from games.balatro.env.select_blind import select_blind_exact

    selected = select_blind_exact(run)

    assert selected.public.blind.tag_key is None
    assert run.public.blind.tag_key == "tag_double"


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


def test_env_r4_ordinary_play_scores_exact_materialized_droll():
    baseline = None
    run = None
    indices = None
    for attempt in range(500):
        candidate = _play_run(seed=f"R4-DROLL-{attempt}")
        by_suit = {}
        for index, card in enumerate(candidate.public.hand):
            by_suit.setdefault(card.suit, []).append(index)
        flush = next(
            (positions[:5] for positions in by_suit.values() if len(positions) >= 5),
            None,
        )
        if flush is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-DROLL-{attempt}")
            indices = tuple(flush)
            break

    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_droll", 1, 4, None, 4, False)
        )
    ]
    selected_chips = 35 + sum(
        BalatroScorer.RANK_CHIPS[run.public.hand[index].rank] for index in indices
    )

    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)

    assert result.public.last_played_hand == "FLUSH"
    assert result.public.score - baseline_result.public.score == selected_chips * 10
    assert type(result.public.jokers[0]).__name__ == "DrollJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_odd_todd():
    baseline = _play_run(seed="R4-ODD-TODD")
    run = _play_run(seed="R4-ODD-TODD")
    odd_index = next(
        index
        for index, card in enumerate(run.public.hand)
        if card.rank in {"A", "3", "5", "7", "9"}
    )
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_odd_todd", 1, 4, None, 4, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (odd_index,))
    result = apply_supported_ordinary_play(run, (odd_index,))

    assert result.public.score - baseline_result.public.score == 31
    assert type(result.public.jokers[0]).__name__ == "OddToddJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_even_steven():
    baseline = _play_run(seed="R4-EVEN-STEVEN")
    run = _play_run(seed="R4-EVEN-STEVEN")
    even_index = next(
        index
        for index, card in enumerate(run.public.hand)
        if card.rank in {"2", "4", "6", "8", "10"}
    )
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_even_steven", 1, 4, None, 4, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (even_index,))
    result = apply_supported_ordinary_play(run, (even_index,))

    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 4
    )
    assert type(result.public.jokers[0]).__name__ == "EvenStevenJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_devious():
    baseline = None
    run = None
    indices = None
    for attempt in range(500):
        candidate = _play_run(seed=f"R4-DEVIOUS-{attempt}")
        straight = next(
            (
                positions
                for positions in combinations(range(len(candidate.public.hand)), 5)
                if HandEvaluator().contains(
                    [candidate.public.hand[index] for index in positions],
                    PokerHand.STRAIGHT,
                )
            ),
            None,
        )
        if straight is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-DEVIOUS-{attempt}")
            indices = tuple(straight)
            break

    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_devious", 1, 4, None, 4, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)

    assert result.public.last_played_hand == "STRAIGHT"
    assert result.public.score - baseline_result.public.score == 400
    assert type(result.public.jokers[0]).__name__ == "DeviousJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_gluttonous():
    baseline = _play_run(seed="R4-GLUTTONOUS")
    run = _play_run(seed="R4-GLUTTONOUS")
    club_index = next(
        index for index, card in enumerate(run.public.hand) if card.suit == "Clubs"
    )
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_gluttenous_joker", 1, 5, None, 5, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (club_index,))
    result = apply_supported_ordinary_play(run, (club_index,))

    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 3
    )
    assert type(result.public.jokers[0]).__name__ == "GluttonousJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_scholar():
    baseline = None
    run = None
    ace_index = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-SCHOLAR-{attempt}")
        candidate_ace = next(
            (
                index
                for index, card in enumerate(candidate.public.hand)
                if card.rank == "A"
            ),
            None,
        )
        if candidate_ace is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-SCHOLAR-{attempt}")
            ace_index = candidate_ace
            break

    assert baseline is not None and run is not None and ace_index is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_scholar", 1, 4, None, 4, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (ace_index,))
    result = apply_supported_ordinary_play(run, (ace_index,))

    assert result.public.score - baseline_result.public.score == 164
    assert type(result.public.jokers[0]).__name__ == "ScholarJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_blue_joker():
    baseline = _play_run(seed="R4-BLUE-JOKER")
    run = _play_run(seed="R4-BLUE-JOKER")
    remaining_draw_cards = len(run.public.deck)
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_blue_joker", 1, 5, None, 5, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score - baseline_result.public.score == (
        remaining_draw_cards * 2
    )
    assert type(result.public.jokers[0]).__name__ == "BlueJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_jolly():
    baseline = None
    run = None
    pair_indices = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-JOLLY-{attempt}")
        pair = next(
            (
                positions
                for positions in combinations(range(len(candidate.public.hand)), 2)
                if candidate.public.hand[positions[0]].rank
                == candidate.public.hand[positions[1]].rank
            ),
            None,
        )
        if pair is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-JOLLY-{attempt}")
            pair_indices = tuple(pair)
            break

    assert baseline is not None and run is not None and pair_indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_jolly", 1, 3, None, 3, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, pair_indices)
    result = apply_supported_ordinary_play(run, pair_indices)

    assert result.public.last_played_hand == "PAIR"
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 4
    )
    assert type(result.public.jokers[0]).__name__ == "JollyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_sly():
    baseline = None
    run = None
    pair_indices = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-SLY-{attempt}")
        pair = next((positions for positions in combinations(range(len(candidate.public.hand)), 2)
                     if candidate.public.hand[positions[0]].rank
                     == candidate.public.hand[positions[1]].rank), None)
        if pair is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-SLY-{attempt}")
            pair_indices = tuple(pair)
            break
    assert baseline is not None and run is not None and pair_indices is not None
    run.public.jokers = [materialize_generated_shop_joker_for_acquisition(
        GeneratedShopJokerItem("j_sly", 1, 3, None, 3, False)
    )]
    baseline_result = apply_supported_ordinary_play(baseline, pair_indices)
    result = apply_supported_ordinary_play(run, pair_indices)
    assert result.public.last_played_hand == "PAIR"
    assert result.public.score - baseline_result.public.score == 100
    assert type(result.public.jokers[0]).__name__ == "SlyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_wily():
    baseline = None
    run = None
    triple_indices = None
    for attempt in range(200):
        candidate = _play_run(seed=f"R4-WILY-{attempt}")
        triple = next(
            (
                positions
                for positions in combinations(range(len(candidate.public.hand)), 3)
                if len({candidate.public.hand[index].rank for index in positions}) == 1
            ),
            None,
        )
        if triple is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-WILY-{attempt}")
            triple_indices = tuple(triple)
            break
    assert baseline is not None and run is not None and triple_indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_wily", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, triple_indices)
    result = apply_supported_ordinary_play(run, triple_indices)
    assert result.public.last_played_hand == "THREE_OF_A_KIND"
    assert result.public.score - baseline_result.public.score == 300
    assert type(result.public.jokers[0]).__name__ == "WilyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_abstract():
    baseline = _play_run(seed="R4-ABSTRACT")
    run = _play_run(seed="R4-ABSTRACT")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_abstract", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 3
    )
    assert type(result.public.jokers[0]).__name__ == "AbstractJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_photograph():
    baseline = None
    run = None
    face_index = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-PHOTOGRAPH-{attempt}")
        index = next(
            (
                card_index
                for card_index, card in enumerate(candidate.public.hand)
                if card.rank in {"J", "Q", "K"}
            ),
            None,
        )
        if index is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-PHOTOGRAPH-{attempt}")
            face_index = index
            break
    assert baseline is not None and run is not None and face_index is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_photograph", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (face_index,))
    result = apply_supported_ordinary_play(run, (face_index,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score == baseline_result.public.score * 2
    assert type(result.public.jokers[0]).__name__ == "PhotographJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_half():
    baseline = _play_run(seed="R4-HALF")
    run = _play_run(seed="R4-HALF")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_half", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 20
    )
    assert type(result.public.jokers[0]).__name__ == "HalfJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_mystic_summit():
    baseline = _play_run(seed="R4-MYSTIC-SUMMIT")
    run = _play_run(seed="R4-MYSTIC-SUMMIT")
    baseline.public.discards_remaining = 0
    run.public.discards_remaining = 0
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_mystic_summit", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 15
    )
    assert type(result.public.jokers[0]).__name__ == "MysticSummitJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_banner():
    baseline = _play_run(seed="R4-BANNER")
    run = _play_run(seed="R4-BANNER")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_banner", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score - baseline_result.public.score == 90
    assert type(result.public.jokers[0]).__name__ == "BannerJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_scary_face():
    baseline = _play_run(seed="R4-SCARY-FACE")
    run = _play_run(seed="R4-SCARY-FACE")
    face_index = next(
        index
        for index, card in enumerate(run.public.hand)
        if card.rank in {"J", "Q", "K"}
    )
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_scary_face", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (face_index,))
    result = apply_supported_ordinary_play(run, (face_index,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score - baseline_result.public.score == 30
    assert type(result.public.jokers[0]).__name__ == "ScaryFaceJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_walkie_talkie():
    baseline = _play_run(seed="R4-WALKIE-TALKIE")
    run = _play_run(seed="R4-WALKIE-TALKIE")
    rank_index = next(
        index
        for index, card in enumerate(run.public.hand)
        if card.rank in {"4", "10"}
    )
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_walkie_talkie", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (rank_index,))
    result = apply_supported_ordinary_play(run, (rank_index,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score == (baseline_result.public.score + 10) * 5
    assert type(result.public.jokers[0]).__name__ == "WalkieTalkieJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_smiley_face():
    baseline = _play_run(seed="R4-SMILEY-FACE")
    run = _play_run(seed="R4-SMILEY-FACE")
    face_index = next(
        index
        for index, card in enumerate(run.public.hand)
        if card.rank in {"J", "Q", "K"}
    )
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_smiley", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (face_index,))
    result = apply_supported_ordinary_play(run, (face_index,))
    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.score == baseline_result.public.score * 6
    assert type(result.public.jokers[0]).__name__ == "SmileyFaceJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_raised_fist():
    baseline = _play_run(seed="R4-RAISED-FIST")
    run = _play_run(seed="R4-RAISED-FIST")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_raised_fist", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    held = run.public.hand[1:]
    rank_values = {str(value): value for value in range(2, 11)}
    rank_values.update({"J": 10, "Q": 10, "K": 10, "A": 11})
    raised_mult = min(rank_values[card.rank] for card in held) * 2
    result = apply_supported_ordinary_play(run, (0,))
    assert result.public.score == baseline_result.public.score * (1 + raised_mult)
    assert type(result.public.jokers[0]).__name__ == "RaisedFistJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_clever_joker():
    baseline = None
    run = None
    indices = None
    for attempt in range(200):
        candidate = _play_run(seed=f"R4-CLEVER-{attempt}")
        by_rank = {}
        for index, card in enumerate(candidate.public.hand):
            by_rank.setdefault(card.rank, []).append(index)
        pairs = [positions[:2] for positions in by_rank.values() if len(positions) >= 2]
        if len(pairs) >= 2:
            baseline = candidate
            run = _play_run(seed=f"R4-CLEVER-{attempt}")
            indices = tuple(pairs[0] + pairs[1])
            break
    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_clever", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)
    assert result.public.last_played_hand == "TWO_PAIR"
    assert result.public.score - baseline_result.public.score == 160
    assert type(result.public.jokers[0]).__name__ == "CleverJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_mad_joker():
    baseline = None
    run = None
    indices = None
    for attempt in range(200):
        candidate = _play_run(seed=f"R4-MAD-{attempt}")
        by_rank = {}
        for index, card in enumerate(candidate.public.hand):
            by_rank.setdefault(card.rank, []).append(index)
        pairs = [positions[:2] for positions in by_rank.values() if len(positions) >= 2]
        if len(pairs) >= 2:
            baseline = candidate
            run = _play_run(seed=f"R4-MAD-{attempt}")
            indices = tuple(pairs[0] + pairs[1])
            break
    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_mad", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)
    assert result.public.last_played_hand == "TWO_PAIR"
    assert result.public.score == baseline_result.public.score * 6
    assert type(result.public.jokers[0]).__name__ == "MadJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_zany_joker():
    baseline = None
    run = None
    indices = None
    for attempt in range(200):
        candidate = _play_run(seed=f"R4-ZANY-{attempt}")
        by_rank = {}
        for index, card in enumerate(candidate.public.hand):
            by_rank.setdefault(card.rank, []).append(index)
        triples = [positions[:3] for positions in by_rank.values() if len(positions) >= 3]
        if triples:
            baseline = candidate
            run = _play_run(seed=f"R4-ZANY-{attempt}")
            indices = tuple(triples[0])
            break
    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_zany", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)
    assert result.public.last_played_hand == "THREE_OF_A_KIND"
    assert result.public.score == baseline_result.public.score * 5
    assert type(result.public.jokers[0]).__name__ == "ZanyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_crafty_joker():
    baseline = None
    run = None
    indices = None
    for attempt in range(200):
        candidate = _play_run(seed=f"R4-CRAFTY-{attempt}")
        by_suit = {}
        for index, card in enumerate(candidate.public.hand):
            by_suit.setdefault(card.suit, []).append(index)
        flushes = [positions[:5] for positions in by_suit.values() if len(positions) >= 5]
        if flushes:
            baseline = candidate
            run = _play_run(seed=f"R4-CRAFTY-{attempt}")
            indices = tuple(flushes[0])
            break
    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_crafty", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)
    assert result.public.last_played_hand == "FLUSH"
    assert result.public.score - baseline_result.public.score == 320
    assert type(result.public.jokers[0]).__name__ == "CraftyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_crazy_joker():
    baseline = None
    run = None
    indices = None
    for attempt in range(200):
        candidate = _play_run(seed=f"R4-CRAZY-{attempt}")
        straights = [
            positions
            for positions in combinations(range(len(candidate.public.hand)), 5)
            if HandEvaluator().contains(
                [candidate.public.hand[index] for index in positions],
                PokerHand.STRAIGHT,
            )
        ]
        if straights:
            baseline = candidate
            run = _play_run(seed=f"R4-CRAZY-{attempt}")
            indices = tuple(straights[0])
            break
    assert baseline is not None and run is not None and indices is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_crazy", 1, 4, None, 4, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, indices)
    result = apply_supported_ordinary_play(run, indices)
    assert result.public.last_played_hand == "STRAIGHT"
    assert result.public.score == baseline_result.public.score * 4
    assert type(result.public.jokers[0]).__name__ == "CrazyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_greedy_joker():
    baseline = None
    run = None
    diamond_index = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-GREEDY-{attempt}")
        index = next(
            (
                card_index
                for card_index, card in enumerate(candidate.public.hand)
                if card.suit == "Diamonds"
            ),
            None,
        )
        if index is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-GREEDY-{attempt}")
            diamond_index = index
            break
    assert baseline is not None and run is not None and diamond_index is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_greedy_joker", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (diamond_index,))
    result = apply_supported_ordinary_play(run, (diamond_index,))
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 3
    )
    assert type(result.public.jokers[0]).__name__ == "GreedyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_lusty_joker():
    baseline = None
    run = None
    heart_index = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-LUSTY-{attempt}")
        index = next(
            (
                index
                for index, card in enumerate(candidate.public.hand)
                if card.suit == "Hearts"
            ),
            None,
        )
        if index is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-LUSTY-{attempt}")
            heart_index = index
            break
    assert baseline is not None and run is not None and heart_index is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_lusty_joker", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (heart_index,))
    result = apply_supported_ordinary_play(run, (heart_index,))
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 3
    )
    assert type(result.public.jokers[0]).__name__ == "LustyJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_wrathful_joker():
    baseline = None
    run = None
    spade_index = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-WRATHFUL-{attempt}")
        index = next(
            (
                index
                for index, card in enumerate(candidate.public.hand)
                if card.suit == "Spades"
            ),
            None,
        )
        if index is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-WRATHFUL-{attempt}")
            spade_index = index
            break
    assert baseline is not None and run is not None and spade_index is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_wrathful_joker", 1, 5, None, 5, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (spade_index,))
    result = apply_supported_ordinary_play(run, (spade_index,))
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 3
    )
    assert type(result.public.jokers[0]).__name__ == "WrathfulJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_fibonacci():
    baseline = None
    run = None
    fibonacci_index = None
    for attempt in range(52):
        candidate = _play_run(seed=f"R4-FIBONACCI-{attempt}")
        index = next(
            (
                index
                for index, card in enumerate(candidate.public.hand)
                if card.rank in {"A", "2", "3", "5", "8"}
            ),
            None,
        )
        if index is not None:
            baseline = candidate
            run = _play_run(seed=f"R4-FIBONACCI-{attempt}")
            fibonacci_index = index
            break
    assert baseline is not None and run is not None and fibonacci_index is not None
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_fibonacci", 2, 8, None, 8, False)
        )
    ]
    baseline_result = apply_supported_ordinary_play(baseline, (fibonacci_index,))
    result = apply_supported_ordinary_play(run, (fibonacci_index,))
    assert result.public.score - baseline_result.public.score == (
        baseline_result.public.score * 8
    )
    assert type(result.public.jokers[0]).__name__ == "FibonacciJoker"


def test_env_r4_ordinary_play_admits_exact_materialized_juggler_noop_callback():
    baseline = _play_run(seed="R4-JUGGLER-PLAY")
    run = _play_run(seed="R4-JUGGLER-PLAY")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_juggler", 1, 4, None, 4, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == baseline_result.public.score
    assert result.public.hand_size == baseline_result.public.hand_size
    assert type(result.public.jokers[0]).__name__ == "JugglerJoker"


def test_env_r4_ordinary_play_admits_exact_materialized_drunkard_noop_callback():
    baseline = _play_run(seed="R4-DRUNKARD-PLAY")
    run = _play_run(seed="R4-DRUNKARD-PLAY")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_drunkard", 1, 4, None, 4, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == baseline_result.public.score
    assert result.public.discards_remaining == baseline_result.public.discards_remaining
    assert type(result.public.jokers[0]).__name__ == "DrunkardJoker"


def test_env_r4_ordinary_play_admits_exact_materialized_golden_noop_callback():
    baseline = _play_run(seed="R4-GOLDEN-PLAY")
    run = _play_run(seed="R4-GOLDEN-PLAY")
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_golden", 1, 6, None, 6, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == baseline_result.public.score
    assert result.public.money == baseline_result.public.money
    assert type(result.public.jokers[0]).__name__ == "GoldenJoker"


def test_env_r4_ordinary_play_scores_exact_materialized_bull_from_money():
    baseline = _play_run(seed="R4-BULL-PLAY")
    run = _play_run(seed="R4-BULL-PLAY")
    run.public.money = 7
    baseline.public.money = 7
    run.public.jokers = [
        materialize_generated_shop_joker_for_acquisition(
            GeneratedShopJokerItem("j_bull", 2, 6, None, 6, False)
        )
    ]

    baseline_result = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score - baseline_result.public.score == 14
    assert result.public.money == baseline_result.public.money == 7
    assert type(result.public.jokers[0]).__name__ == "BullJoker"


@pytest.mark.parametrize(
    "held_item",
    [PlanetCard("Mercury", "PAIR", 15, 1), Fool()],
)
def test_env_r4_ordinary_play_admits_profile_consumables_as_play_time_no_ops(
    held_item,
):
    baseline = _play_run(seed="R4-HELD-NO-OP")
    held = _play_run(seed="R4-HELD-NO-OP")
    held.public.consumables = [held_item]

    expected = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(held, (0,))

    assert result.public.score == expected.public.score
    assert result.public.hand == expected.public.hand
    assert len(result.public.consumables) == 1
    assert type(result.public.consumables[0]) is type(held_item)
    assert result.public.consumables[0].name == held_item.name


@pytest.mark.parametrize(
    "held_item",
    [
        GeneratedShopConsumableItem("Tarot", "c_fool", 3, 3, False),
        GeneratedShopConsumableItem("Planet", "c_mercury", 3, 2, True),
    ],
)
def test_env_r4_ordinary_play_admits_generated_consumable_descriptors_as_play_time_no_ops(
    held_item,
):
    baseline = _play_run(seed="R4-GENERATED-HELD-NO-OP")
    held = _play_run(seed="R4-GENERATED-HELD-NO-OP")
    held.public.consumables = [held_item]

    expected = apply_supported_ordinary_play(baseline, (0,))
    result = apply_supported_ordinary_play(held, (0,))

    assert result.public.score == expected.public.score
    assert result.public.hand == expected.public.hand
    assert result.public.consumables == [held_item]


@pytest.mark.parametrize(
    "held_item",
    [
        GeneratedShopConsumableItem("Spectral", "c_aura", 4, 4),
        GeneratedShopConsumableItem("Tarot", "c_mercury", 3, 3),
        GeneratedShopConsumableItem("Planet", "c_unknown", 3, 3),
        GeneratedShopConsumableItem("Tarot", "c_fool", True, 3),
        GeneratedShopConsumableItem("Tarot", "c_fool", 3, -1),
        GeneratedShopConsumableItem("Tarot", "c_fool", 3, 3, "yes"),
    ],
)
def test_env_r4_ordinary_play_rejects_unowned_or_malformed_generated_consumables(
    held_item,
):
    run = _play_run(seed="R4-GENERATED-HELD-REJECT")
    run.public.consumables = [held_item]

    with pytest.raises(HeadlessTransitionError, match="held consumable"):
        apply_supported_ordinary_play(run, (0,))


def test_env_r4_ordinary_play_admits_applied_voucher_and_rejects_observatory():
    supported = _play_run(seed="R4-VOUCHER-NO-OP")
    supported.public.vouchers = ["v_seed_money"]
    supported.public.vouchers_observed = True
    result = apply_supported_ordinary_play(supported, (0,))
    assert result.public.vouchers == ["v_seed_money"]

    unobserved = _play_run(seed="R4-VOUCHER-UNOBSERVED")
    unobserved.public.vouchers = ["v_seed_money"]
    with pytest.raises(HeadlessTransitionError, match="Voucher hand size"):
        apply_supported_ordinary_play(unobserved, (0,))

    observatory = _play_run(seed="R4-OBSERVATORY")
    observatory.public.vouchers = ["v_observatory"]
    observatory.public.consumables = [PlanetCard("Mercury", "PAIR", 15, 1)]
    with pytest.raises(HeadlessTransitionError, match="Voucher action-time"):
        apply_supported_ordinary_play(observatory, (0,))


def test_env_r4_ordinary_play_rejects_invalid_selection_and_stale_private_zone():
    run = _play_run()
    with pytest.raises(HeadlessTransitionError, match="distinct"):
        apply_supported_ordinary_play(run, (0, 0))

    stale = _play_run(seed="R4-STALE")
    stale.draw_pile.pop()
    with pytest.raises(HeadlessTransitionError, match="private/public draw zones"):
        apply_supported_ordinary_play(stale, (0,))
