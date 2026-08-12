from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan, Magician, Strength


def _state(cards: list[BalatroCard]) -> BalatroState:
    state = BalatroState()
    state.hand = cards
    state.deck = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in cards
    ]
    return state


def test_strength_prefers_promoting_four_without_damaging_fibonacci_five():
    four = BalatroCard("4", "Clubs")
    five = BalatroCard("5", "Hearts")
    state = _state([four, five])
    state.jokers = [FibonacciJoker()]

    ranked = ContextualConsumableTargetEvaluator().rank_targets(state, Strength())

    assert ranked
    assert ranked[0].target_indices == (0,)
    assert ranked[0].cards == (four,)
    assert ranked[0].contextual_delta > 0.0
    assert ranked[0].total_gain > ranked[-1].total_gain


def test_multi_target_transform_prefers_using_full_safe_capacity():
    first = BalatroCard("7", "Hearts")
    second = BalatroCard("9", "Clubs")
    state = _state([first, second])

    recommendation = ContextualConsumableTargetEvaluator().recommend(state, Magician())

    assert recommendation is not None
    assert recommendation.target_indices == (0, 1)
    assert recommendation.effective_changes == 2
    assert recommendation.overwrite_penalty == 0.0


def test_targeting_avoids_overwriting_existing_enhancement_when_plain_target_exists():
    plain = BalatroCard("7", "Hearts")
    glass = BalatroCard("9", "Clubs", enhancement="Glass")
    state = _state([plain, glass])

    recommendation = ContextualConsumableTargetEvaluator().recommend(state, Magician())

    assert recommendation is not None
    assert recommendation.target_indices == (0,)
    assert recommendation.cards == (plain,)
    assert recommendation.overwrite_penalty == 0.0

    glass_only = next(
        evaluation
        for evaluation in ContextualConsumableTargetEvaluator().rank_targets(state, Magician())
        if evaluation.target_indices == (1,)
    )
    assert glass_only.overwrite_penalty > 0.0
    assert recommendation.total_gain > glass_only.total_gain


def test_destructive_tarot_remains_fail_closed_for_target_quality_slice():
    state = _state([BalatroCard("2", "Hearts"), BalatroCard("3", "Clubs")])
    evaluator = ContextualConsumableTargetEvaluator()

    assert not evaluator.supports(HangedMan())
    assert evaluator.rank_targets(state, HangedMan()) == ()
    assert evaluator.recommend(state, HangedMan()) is None


def test_target_simulation_does_not_mutate_authoritative_state():
    four = BalatroCard("4", "Clubs")
    five = BalatroCard("5", "Hearts", enhancement="Glass")
    state = _state([four, five])
    state.jokers = [FibonacciJoker()]
    before_hand = [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.hand
    ]
    before_deck = [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.deck
    ]

    ContextualConsumableTargetEvaluator().rank_targets(state, Strength())

    assert [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.hand
    ] == before_hand
    assert [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.deck
    ] == before_deck
