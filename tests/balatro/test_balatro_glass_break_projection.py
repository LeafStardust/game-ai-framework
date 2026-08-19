from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.canio import CanioJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, *, jokers=(), owned_deck=None):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    state.owned_deck = None if owned_deck is None else list(owned_deck)
    return state


def _project(cards, state, hand):
    return VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_scored_glass_breaks_without_canio_and_updates_owned_deck():
    played = BalatroCard("A", "Spades", enhancement="Glass", live_id=11)
    owned_glass = BalatroCard("A", "Spades", enhancement="Glass", live_id=11)
    owned_other = BalatroCard("K", "Hearts", live_id=12)
    state = _state(
        [played],
        owned_deck=[owned_glass, owned_other],
    )

    transition = _project([played], state, PokerHand.HIGH_CARD)

    assert transition.joker_projection_complete is True
    assert transition.distribution.random_sources == ("Glass break x1",)
    assert [
        (outcome.score, round(outcome.probability, 10))
        for outcome in transition.distribution.outcomes
    ] == [
        (32, 0.75),
        (32, 0.25),
    ]

    no_break, broken = transition.distribution.outcomes
    assert no_break.state_after_scoring.glass_cards_destroyed == 0
    assert len(no_break.state_after_scoring.owned_deck) == 2
    assert broken.state_after_scoring.glass_cards_destroyed == 1
    assert [card.live_id for card in broken.state_after_scoring.owned_deck] == [12]


def test_non_scoring_glass_kicker_does_not_roll_break_probability():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("2", "Hearts", enhancement="Glass"),
    ]
    state = _state(cards)

    transition = _project(cards, state, PokerHand.PAIR)

    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 60
    assert transition.distribution.random_sources == ()


def test_retriggered_glass_scores_again_but_rolls_break_only_once():
    card = BalatroCard(
        "A",
        "Spades",
        enhancement="Glass",
        seal="Red",
        live_id=21,
    )
    state = _state([card])

    transition = _project([card], state, PokerHand.HIGH_CARD)

    assert transition.distribution.random_sources == ("Glass break x1",)
    assert [
        (outcome.score, round(outcome.probability, 10))
        for outcome in transition.distribution.outcomes
    ] == [
        (108, 0.75),
        (108, 0.25),
    ]


def test_multiple_glass_cards_preserve_distinct_break_states():
    first = BalatroCard("10", "Spades", enhancement="Glass", live_id=31)
    second = BalatroCard("10", "Hearts", enhancement="Glass", live_id=32)
    other = BalatroCard("K", "Clubs", live_id=33)
    owned = [
        BalatroCard("10", "Spades", enhancement="Glass", live_id=31),
        BalatroCard("10", "Hearts", enhancement="Glass", live_id=32),
        other,
    ]
    state = _state([first, second], owned_deck=owned)

    transition = _project([first, second], state, PokerHand.PAIR)

    assert transition.distribution.random_sources == ("Glass break x2",)
    assert {
        tuple(card.live_id for card in outcome.state_after_scoring.owned_deck): (
            outcome.score,
            round(outcome.probability, 10),
        )
        for outcome in transition.distribution.outcomes
    } == {
        (31, 32, 33): (240, 0.5625),
        (32, 33): (240, 0.1875),
        (31, 33): (240, 0.1875),
        (33,): (240, 0.0625),
    }
    assert sorted(
        outcome.state_after_scoring.glass_cards_destroyed
        for outcome in transition.distribution.outcomes
    ) == [0, 1, 1, 2]


def test_canio_grows_only_when_broken_glass_card_is_face():
    ace = BalatroCard("A", "Spades", enhancement="Glass", live_id=41)
    state = _state([ace], jokers=[CanioJoker()])

    transition = _project([ace], state, PokerHand.HIGH_CARD)

    assert transition.distribution.random_sources == ("Glass break x1",)
    assert [
        next(
            joker
            for joker in outcome.state_after_scoring.jokers
            if isinstance(joker, CanioJoker)
        ).x_mult
        for outcome in transition.distribution.outcomes
    ] == [1.0, 1.0]


def test_debuffed_glass_card_cannot_break():
    card = BalatroCard(
        "A",
        "Spades",
        enhancement="Glass",
        debuffed=True,
    )
    state = _state([card])

    transition = _project([card], state, PokerHand.HIGH_CARD)

    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 5
    assert transition.distribution.random_sources == ()
