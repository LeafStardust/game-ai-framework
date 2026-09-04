from math import ceil

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.transition import HeadlessRunState
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _flint_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Flint"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hands_remaining = 1
    state.discards_remaining = 1
    return HeadlessRunState(public=state, seed="FLINT")


def _expected_level_one_flint_score(evaluator, state, cards) -> tuple[int, int, int]:
    rules = hand_rules_for_state(state)
    hand = evaluator.hand_evaluator.evaluate(cards, rules=rules)
    base = BalatroScorer.SCORES[hand]
    scoring_cards = evaluator.score_outcomes.scorer.scoring_cards(
        hand,
        cards,
        rules=rules,
    )
    card_chips = sum(
        BalatroScorer.RANK_CHIPS[card.rank]
        for card in scoring_cards
        if not bool(getattr(card, "debuffed", False))
    )
    flint_base_chips = max(ceil(base.chips / 2), 0)
    flint_base_mult = max(ceil(base.mult / 2), 1)
    return (
        (flint_base_chips + card_chips) * flint_base_mult,
        flint_base_chips,
        flint_base_mult,
    )


def test_env_r2_flint_projection_halves_only_base_chips_and_mult_before_card_chips():
    started = start_supported_start_inert_boss(_flint_run())
    evaluator = LiveHandDecisionEvaluator()
    cards = list(started.public.hand[:5])
    action = BalatroAction(PLAY_CARDS, cards=cards)

    assert boss_play_action_is_legal(started.public, action)

    expected_total, expected_base_chips, expected_base_mult = _expected_level_one_flint_score(
        evaluator,
        started.public,
        cards,
    )
    projection = evaluator.project_play(started.public, action)

    rules = hand_rules_for_state(started.public)
    hand = evaluator.hand_evaluator.evaluate(cards, rules=rules)
    ordinary_base = BalatroScorer.SCORES[hand]
    assert expected_base_chips == ceil(ordinary_base.chips / 2)
    assert expected_base_mult == ceil(ordinary_base.mult / 2)
    assert projection.hand_score == expected_total
    assert projection.expected_hand_score == float(expected_total)
    assert projection.maximum_hand_score == expected_total


def test_env_r2_flint_projection_is_lower_than_same_unmodified_boss_free_play():
    started = start_supported_start_inert_boss(_flint_run())
    cards = list(started.public.hand[:5])
    action = BalatroAction(PLAY_CARDS, cards=cards)

    flint = LiveHandDecisionEvaluator().project_play(started.public, action)

    ordinary_state = started.public.copy()
    ordinary_state.boss_name = None
    ordinary = LiveHandDecisionEvaluator().project_play(ordinary_state, action)

    assert flint.hand == ordinary.hand
    assert flint.hand_score < ordinary.hand_score
    assert flint.expected_hand_score < ordinary.expected_hand_score


def test_env_r2_flint_projection_does_not_mutate_started_state_or_rng():
    started = start_supported_start_inert_boss(_flint_run())
    evaluator = LiveHandDecisionEvaluator()
    before_hand = list(started.public.hand)
    before_score = started.public.score
    before_rng = started.rng_snapshot()

    evaluator.project_play(
        started.public,
        BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:5])),
    )

    assert started.public.hand == before_hand
    assert started.public.score == before_score
    assert started.rng_snapshot() == before_rng
