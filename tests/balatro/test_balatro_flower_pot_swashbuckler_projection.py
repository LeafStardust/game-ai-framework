from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.flower_pot import FlowerPotJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.swashbuckler import SwashbucklerJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(jokers, cards, hand):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)

    transition = VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    return transition.distribution.minimum


def test_flower_pot_triggers_from_four_distinct_scoring_suits():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Diamonds"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Spades"),
    ]

    assert _project(
        [SplashJoker(), FlowerPotJoker()],
        cards,
        PokerHand.HIGH_CARD,
    ) == 57


def test_flower_pot_ignores_non_scoring_kicker_suits():
    cards = [
        BalatroCard("10", "Hearts"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("2", "Clubs"),
        BalatroCard("3", "Spades"),
    ]

    assert _project([FlowerPotJoker()], cards, PokerHand.PAIR) == 60


def test_flower_pot_does_not_reuse_one_wild_for_multiple_suits():
    cards = [
        BalatroCard("2", "Hearts", enhancement="Wild"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
    ]

    assert _project(
        [SplashJoker(), FlowerPotJoker()],
        cards,
        PokerHand.HIGH_CARD,
    ) == 19


def test_flower_pot_respects_smeared_with_distinct_red_and_black_cards():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Clubs"),
    ]

    assert _project(
        [SmearedJoker(), SplashJoker(), FlowerPotJoker()],
        cards,
        PokerHand.HIGH_CARD,
    ) == 57


def test_swashbuckler_uses_other_joker_live_sell_cost_and_excludes_itself():
    swashbuckler = SwashbucklerJoker()
    swashbuckler.sell_cost = 50
    four_fingers = FourFingersJoker()
    four_fingers.sell_cost = 7
    cards = [BalatroCard("A", "Spades")]

    assert _project(
        [swashbuckler, four_fingers],
        cards,
        PokerHand.HIGH_CARD,
    ) == 128


def test_swashbuckler_uses_modeled_sell_value_when_generic_cost_is_absent():
    swashbuckler = SwashbucklerJoker()
    egg = EggJoker()
    egg.sell_value = 12
    cards = [BalatroCard("A", "Spades")]

    assert _project(
        [swashbuckler, egg],
        cards,
        PokerHand.HIGH_CARD,
    ) == 208
