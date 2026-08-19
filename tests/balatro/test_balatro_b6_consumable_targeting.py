from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.spectrals import Aura, Cryptid, DejaVu, Medium, Talisman, Trance
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan, Justice, Magician, Strength


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


def test_justice_never_returns_an_already_glass_noop_target():
    already_glass = BalatroCard("9", "Clubs", enhancement="Glass")
    plain = BalatroCard("7", "Hearts")
    evaluator = ContextualConsumableTargetEvaluator()

    ranked = evaluator.rank_targets(_state([already_glass, plain]), Justice())

    assert [evaluation.target_indices for evaluation in ranked] == [(1,)]
    assert ranked[0].cards == (plain,)
    assert evaluator.rank_targets(_state([already_glass]), Justice()) == ()


def test_hanged_man_is_supported_but_fails_closed_without_complete_owned_deck():
    state = _state([BalatroCard("2", "Hearts"), BalatroCard("3", "Clubs")])
    state.phase = "SELECTING_HAND"
    evaluator = ContextualConsumableTargetEvaluator()

    assert evaluator.supports(HangedMan())
    assert evaluator.rank_targets(state, HangedMan()) == ()
    assert evaluator.recommend(state, HangedMan()) is None


def test_deterministic_seal_spectrals_share_d6_target_ranking():
    state = _state([BalatroCard("7", "Hearts")])
    evaluator = ContextualConsumableTargetEvaluator()

    for spectral_type in (Talisman, DejaVu, Trance, Medium):
        consumable = spectral_type()
        recommendation = evaluator.recommend(state, consumable)

        assert evaluator.supports(consumable)
        assert recommendation is not None
        assert recommendation.target_indices == (0,)
        assert recommendation.effective_changes == 1
        assert recommendation.intrinsic_delta > 0.0
        assert recommendation.total_gain > 0.0


def test_deterministic_seal_spectral_prefers_plain_card_over_seal_overwrite():
    plain = BalatroCard("7", "Hearts")
    blue_seal = BalatroCard("9", "Clubs", seal="Blue")
    state = _state([plain, blue_seal])

    recommendation = ContextualConsumableTargetEvaluator().recommend(state, DejaVu())

    assert recommendation is not None
    assert recommendation.target_indices == (0,)
    assert recommendation.cards == (plain,)


def test_stochastic_or_card_generation_spectrals_remain_fail_closed():
    evaluator = ContextualConsumableTargetEvaluator()

    assert not evaluator.supports(Aura())
    assert not evaluator.supports(Cryptid())


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
