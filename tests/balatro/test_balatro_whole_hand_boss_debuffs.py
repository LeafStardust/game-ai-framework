from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.hiker import HikerJoker
from games.balatro.jokers.matador import MatadorJoker
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(boss_name, cards, jokers=()):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = boss_name
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.jokers = list(jokers)
    state.money = 0
    return state


def _project(state, hand, cards):
    return LiveFinalJokerScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
        include_card_chips=True,
    )


def test_psychic_short_play_is_a_zero_score_hand_not_an_illegal_action():
    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("9", "Diamonds"),
    ]
    state = _state("The Psychic", cards)

    transition = _project(state, PokerHand.HIGH_CARD, cards)

    assert transition.joker_projection_complete is True
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 0
    assert transition.distribution.maximum == 0
    assert state.money == 0


def test_psychic_five_card_play_uses_normal_scoring():
    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Diamonds"),
        BalatroCard("9", "Spades"),
    ]
    state = _state("The Psychic", cards)

    transition = _project(state, PokerHand.HIGH_CARD, cards)

    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16


def test_psychic_debuffed_hand_pays_matador_without_scoring():
    card = BalatroCard("A", "Spades")
    state = _state("The Psychic", [card], [MatadorJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.distribution.minimum == 0
    assert transition.state_after_scoring.money == 8
    assert state.money == 0


def test_blueprint_copy_of_matador_pays_on_debuffed_hand():
    card = BalatroCard("A", "Spades")
    state = _state(
        "The Psychic",
        [card],
        [BlueprintJoker(), MatadorJoker()],
    )

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.distribution.minimum == 0
    assert transition.state_after_scoring.money == 16
    assert state.money == 0


def test_debuffed_hand_skips_unrelated_scoring_and_card_mutation_effects():
    card = BalatroCard("A", "Spades")
    state = _state("The Psychic", [card], [HikerJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.distribution.minimum == 0
    assert card.permanent_bonus == 0
    assert transition.state_after_scoring.hand[0].permanent_bonus == 0


def test_chicot_suppresses_psychic_debuff_and_matador_trigger():
    card = BalatroCard("A", "Spades")
    state = _state(
        "The Psychic",
        [card],
        [MatadorJoker(), ChicotJoker()],
    )

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.distribution.minimum == 16
    assert transition.state_after_scoring.money == 0


def test_eye_records_only_accepted_hand_types_and_rejects_repeats():
    ace = BalatroCard("A", "Spades")
    state = _state("The Eye", [ace])
    state.boss_blind_state_observed = True
    state.boss_blind_hands = set()

    first = _project(state, PokerHand.HIGH_CARD, [ace])

    assert first.distribution.minimum == 16
    assert first.state_after_scoring.boss_blind_hands == {"HIGH_CARD"}
    assert state.boss_blind_hands == set()

    repeated = _project(
        first.state_after_scoring,
        PokerHand.HIGH_CARD,
        [ace],
    )

    assert repeated.distribution.minimum == 0
    assert repeated.state_after_scoring.boss_blind_hands == {"HIGH_CARD"}


def test_eye_accepts_a_new_hand_type_after_an_earlier_accepted_hand():
    cards = [BalatroCard("2", "Spades"), BalatroCard("2", "Hearts")]
    state = _state("The Eye", cards)
    state.boss_blind_state_observed = True
    state.boss_blind_hands = {"HIGH_CARD"}

    transition = _project(state, PokerHand.PAIR, cards)

    assert transition.distribution.minimum == 28
    assert transition.state_after_scoring.boss_blind_hands == {
        "HIGH_CARD",
        "PAIR",
    }


def test_mouth_first_hand_sets_only_hand_and_same_type_remains_scoring():
    cards = [BalatroCard("2", "Spades"), BalatroCard("2", "Hearts")]
    state = _state("The Mouth", cards)
    state.boss_blind_state_observed = True
    state.boss_blind_only_hand = None

    first = _project(state, PokerHand.PAIR, cards)

    assert first.distribution.minimum == 28
    assert first.state_after_scoring.boss_blind_only_hand == "PAIR"
    assert state.boss_blind_only_hand is None

    same = _project(first.state_after_scoring, PokerHand.PAIR, cards)

    assert same.distribution.minimum == 28
    assert same.state_after_scoring.boss_blind_only_hand == "PAIR"


def test_mouth_rejects_different_hand_without_replacing_only_hand():
    card = BalatroCard("A", "Spades")
    state = _state("The Mouth", [card], [MatadorJoker()])
    state.boss_blind_state_observed = True
    state.boss_blind_only_hand = "PAIR"

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.distribution.minimum == 0
    assert transition.state_after_scoring.money == 8
    assert transition.state_after_scoring.boss_blind_only_hand == "PAIR"
    assert state.money == 0
