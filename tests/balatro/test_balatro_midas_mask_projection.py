from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers, *, owned_deck=None):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    if owned_deck is not None:
        state.owned_deck = list(owned_deck)
    return state


def _project(state, hand, cards):
    return VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_midas_mask_transforms_only_scoring_face_cards_on_isolated_branch():
    cards = [
        BalatroCard("K", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
    ]
    state = _state(cards, [MidasMaskJoker()])

    transition = _project(state, PokerHand.PAIR, cards)

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 60
    assert [card.enhancement for card in transition.state_after_scoring.hand] == [
        "Gold",
        "Gold",
        None,
    ]
    assert [card.enhancement for card in cards] == [None, None, None]


def test_midas_mask_replaces_scoring_enhancement_before_same_hand_score():
    king = BalatroCard("K", "Spades", enhancement="Mult")
    state = _state([king], [MidasMaskJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [king])

    # The Mult enhancement is replaced before card scoring, so it cannot add +4 Mult.
    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 15
    assert transition.state_after_scoring.hand[0].enhancement == "Gold"
    assert king.enhancement == "Mult"


def test_midas_mask_uses_pareidolia_face_rule():
    ace = BalatroCard("A", "Spades")
    state = _state([ace], [PareidoliaJoker(), MidasMaskJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 16
    assert transition.state_after_scoring.hand[0].enhancement == "Gold"
    assert ace.enhancement is None


def test_midas_mask_does_not_transform_debuffed_face_card():
    king = BalatroCard("K", "Spades", debuffed=True)
    state = _state([king], [MidasMaskJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [king])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 5
    assert transition.state_after_scoring.hand[0].enhancement is None


def test_midas_before_vampire_feeds_gold_to_vampire_same_hand():
    king = BalatroCard("K", "Spades")
    vampire = VampireJoker()
    state = _state([king], [MidasMaskJoker(), vampire])

    transition = _project(state, PokerHand.HIGH_CARD, [king])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 16
    assert transition.state_after_scoring.hand[0].enhancement is None
    projected_vampire = transition.state_after_scoring.jokers[1]
    assert projected_vampire.x_mult == 1.1
    assert vampire.x_mult == 1.0
    assert king.enhancement is None


def test_vampire_before_midas_leaves_new_gold_card_and_no_vampire_growth():
    king = BalatroCard("K", "Spades")
    vampire = VampireJoker()
    state = _state([king], [vampire, MidasMaskJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [king])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 15
    assert transition.state_after_scoring.hand[0].enhancement == "Gold"
    projected_vampire = transition.state_after_scoring.jokers[0]
    assert projected_vampire.x_mult == 1.0
    assert vampire.x_mult == 1.0
    assert king.enhancement is None


def test_midas_mutation_syncs_owned_deck_and_can_activate_drivers_license():
    played_king = BalatroCard("K", "Spades", live_id=7)
    owned_king = BalatroCard("K", "Spades", live_id=7)
    enhanced = [
        BalatroCard(
            str((index % 8) + 2),
            "Hearts",
            enhancement="Bonus",
            live_id=100 + index,
        )
        for index in range(15)
    ]
    owned_deck = [owned_king, *enhanced]
    state = _state(
        [played_king],
        [MidasMaskJoker(), DriversLicenseJoker()],
        owned_deck=owned_deck,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [played_king])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 45
    assert transition.state_after_scoring.hand[0].enhancement == "Gold"
    projected_owned_king = next(
        card
        for card in transition.state_after_scoring.owned_deck
        if card.live_id == 7
    )
    assert projected_owned_king is transition.state_after_scoring.hand[0]
    assert projected_owned_king.enhancement == "Gold"
    assert played_king.enhancement is None
    assert owned_king.enhancement is None
