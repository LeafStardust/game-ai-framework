from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan


class _Estimator:
    def estimate(self, state, action):
        return 1.0, ("fixture consumable value",)


def _state(hand, deck, *, phase="TAROT_PACK"):
    state = BalatroState()
    state.phase = phase
    state.hand = list(hand)
    state.deck = list(deck)
    return state


def _choice():
    return LivePackChoice(
        area_index=0,
        address=0x1000,
        data={
            "area_index": 0,
            "address": 0x1000,
            "live_id": 501,
            "label": "The Hanged Man",
            "ability_name": "The Hanged Man",
            "ability_set": "Tarot",
        },
    )


def test_hanged_man_pack_prefers_two_low_value_cards_and_avoids_steel():
    two = BalatroCard("2", "Hearts")
    steel_ace = BalatroCard("A", "Spades", enhancement="Steel")
    three = BalatroCard("3", "Clubs")
    state = _state(
        [two, steel_ace, three],
        [
            BalatroCard("K", "Diamonds"),
            BalatroCard("Q", "Hearts"),
            BalatroCard("10", "Spades"),
            BalatroCard("J", "Clubs"),
        ],
    )

    ranked = ContextualConsumableTargetEvaluator().rank_targets(
        state,
        HangedMan(),
    )

    assert ranked
    assert ranked[0].target_indices == (0, 2)
    assert ranked[0].cards == (two, three)
    assert ranked[0].effective_changes == 2
    assert ranked[0].deck_thinning_gain > 0.0
    assert ranked[0].intrinsic_delta > 0.0
    assert ranked[0].total_gain > 0.0
    assert any(
        note == "owned deck source=pack hand + remaining deck"
        for note in ranked[0].rationale
    )


def test_hanged_man_pack_uses_build_context_to_preserve_fibonacci_rank():
    five = BalatroCard("5", "Hearts")
    four = BalatroCard("4", "Clubs")
    six = BalatroCard("6", "Diamonds")
    state = _state(
        [five, four, six],
        [
            BalatroCard("A", "Spades"),
            BalatroCard("2", "Spades"),
            BalatroCard("3", "Hearts"),
            BalatroCard("8", "Clubs"),
        ],
    )
    state.jokers = [FibonacciJoker()]

    recommendation = ContextualConsumableTargetEvaluator().recommend(
        state,
        HangedMan(),
    )

    assert recommendation is not None
    assert recommendation.target_indices == (1, 2)
    assert recommendation.cards == (four, six)
    assert recommendation.contextual_delta > 0.0


def test_hanged_man_held_during_blind_fails_closed_without_owned_deck():
    two = BalatroCard("2", "Hearts")
    three = BalatroCard("3", "Clubs")
    state = _state(
        [two, three],
        [BalatroCard("K", "Spades")],
        phase="SELECTING_HAND",
    )
    evaluator = ContextualConsumableTargetEvaluator()

    assert evaluator.supports(HangedMan())
    assert evaluator.rank_targets(state, HangedMan()) == ()
    assert evaluator.recommend(state, HangedMan()) is None


def test_hanged_man_can_use_explicit_authoritative_owned_deck():
    two = BalatroCard("2", "Hearts")
    steel_ace = BalatroCard("A", "Spades", enhancement="Steel")
    three = BalatroCard("3", "Clubs")
    state = _state(
        [two, steel_ace, three],
        [],
        phase="SELECTING_HAND",
    )
    state.owned_deck = [
        two,
        steel_ace,
        three,
        BalatroCard("K", "Diamonds"),
        BalatroCard("Q", "Hearts"),
    ]

    recommendation = ContextualConsumableTargetEvaluator().recommend(
        state,
        HangedMan(),
    )

    assert recommendation is not None
    assert recommendation.target_indices == (0, 2)
    assert any(
        note == "owned deck source=authoritative owned_deck"
        for note in recommendation.rationale
    )


def test_hanged_man_pack_policy_carries_exact_destroy_targets():
    two = BalatroCard("2", "Hearts")
    steel_ace = BalatroCard("A", "Spades", enhancement="Steel")
    three = BalatroCard("3", "Clubs")
    state = _state(
        [two, steel_ace, three],
        [
            BalatroCard("K", "Diamonds"),
            BalatroCard("Q", "Hearts"),
        ],
    )
    choice = _choice()

    ranked = BalatroPackPolicy(
        item_estimator=_Estimator(),
        skip_bias=0.35,
    ).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    selected = ranked[0]
    assert selected.action.name == SELECT_PACK_CARD
    assert selected.action.target is choice
    assert selected.action.cards == [two, three]
    assert any("deck thinning gain=" in note for note in selected.notes)


def test_hanged_man_targeting_does_not_mutate_authoritative_state():
    two = BalatroCard("2", "Hearts")
    steel_ace = BalatroCard("A", "Spades", enhancement="Steel")
    three = BalatroCard("3", "Clubs")
    state = _state(
        [two, steel_ace, three],
        [BalatroCard("K", "Diamonds")],
    )
    before_hand = [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.hand
    ]
    before_deck = [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.deck
    ]

    ContextualConsumableTargetEvaluator().rank_targets(
        state,
        HangedMan(),
    )

    assert [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.hand
    ] == before_hand
    assert [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.deck
    ] == before_deck
