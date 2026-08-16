from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.seance import SeanceJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.superposition import SuperpositionJoker
from games.balatro.jokers.vagabond import VagabondJoker
from games.balatro.live.generated_consumable_outcomes import (
    LiveGeneratedConsumableScoreOutcomeModel,
    ProjectedGeneratedConsumable,
)
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.state import BalatroState


def _state(cards, jokers, *, money=0, consumables=None, consumable_slots=2):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.jokers = list(jokers)
    state.money = money
    state.consumables = list(consumables or [])
    state.consumable_slots = consumable_slots
    return state


def _project(state, hand, cards):
    return LiveGeneratedConsumableScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def _generated_categories(outcome):
    return [
        consumable.category
        for consumable in outcome.state_after_scoring.consumables
        if isinstance(consumable, ProjectedGeneratedConsumable)
    ]


def test_seance_creates_abstract_spectral_without_sampling_identity():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(cards, [SeanceJoker()])

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    assert transition.joker_projection_complete is True
    assert len(transition.distribution.outcomes) == 1
    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert "generated Spectral identity (abstracted)" in transition.distribution.random_sources
    assert state.consumables == []


def test_seance_and_blueprint_fill_two_slots_in_joker_order():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(cards, [BlueprintJoker(), SeanceJoker()])

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    assert _generated_categories(transition.distribution.outcomes[0]) == [
        "SPECTRAL",
        "SPECTRAL",
    ]


def test_generated_consumables_respect_full_slot_capacity():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    held = "held-consumable"
    state = _state(
        cards,
        [SeanceJoker()],
        consumables=[held],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert outcome_state.consumables == [held]


def test_vagabond_checks_money_at_hand_play():
    card = BalatroCard("A", "Spades")
    eligible = _state([card], [VagabondJoker()], money=4)
    blocked = _state([card], [VagabondJoker()], money=5)

    eligible_transition = _project(eligible, PokerHand.HIGH_CARD, [card])
    blocked_transition = _project(blocked, PokerHand.HIGH_CARD, [card])

    assert _generated_categories(eligible_transition.distribution.outcomes[0]) == ["TAROT"]
    assert _generated_categories(blocked_transition.distribution.outcomes[0]) == []


def test_superposition_requires_ace_to_belong_to_the_straight_component():
    cards = [
        BalatroCard("5", "Spades"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Clubs"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("A", "Spades"),
    ]
    state = _state(cards, [FourFingersJoker(), SuperpositionJoker()])

    transition = _project(state, PokerHand.STRAIGHT, cards)

    assert _generated_categories(transition.distribution.outcomes[0]) == []


def test_superposition_counts_debuffed_ace_for_straight_structure():
    cards = [
        BalatroCard("A", "Spades", debuffed=True),
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("5", "Spades"),
    ]
    state = _state(cards, [SuperpositionJoker()])

    transition = _project(state, PokerHand.STRAIGHT, cards)

    assert _generated_categories(transition.distribution.outcomes[0]) == ["TAROT"]


def test_sixth_sense_first_hand_destroys_six_and_creates_one_spectral():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert outcome_state.owned_deck == []
    assert len(state.owned_deck) == 1


def test_sixth_sense_does_not_trigger_after_an_earlier_hand():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [SixthSenseJoker()])
    state.round_hand_play_counts["PAIR"] = 1

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert _generated_categories(transition.distribution.outcomes[0]) == []
    assert len(outcome_state.owned_deck) == 1


def test_sixth_sense_full_slots_prevent_both_creation_and_destruction():
    six = BalatroCard("6", "Hearts", live_id=600)
    held = "held-consumable"
    state = _state(
        [six],
        [SixthSenseJoker()],
        consumables=[held],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert outcome_state.consumables == [held]
    assert len(outcome_state.owned_deck) == 1


def test_duplicate_sixth_sense_only_destroys_the_six_once():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [SixthSenseJoker(), SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert transition.distribution.outcomes[0].state_after_scoring.owned_deck == []


def test_blueprint_does_not_copy_sixth_sense():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state(
        [six],
        [BlueprintJoker(), SixthSenseJoker()],
        consumable_slots=2,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert transition.joker_projection_complete is True


def test_dna_copy_survives_sixth_sense_destruction_of_original():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [DNAJoker(), SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert len(outcome_state.owned_deck) == 1
    assert outcome_state.owned_deck[0].rank == "6"
    assert outcome_state.owned_deck[0].live_id is None


def test_eight_ball_has_exact_one_in_four_creation_branch():
    eight = BalatroCard("8", "Hearts")
    state = _state([eight], [EightBallJoker()], consumable_slots=1)

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    branches = sorted(
        (
            tuple(_generated_categories(outcome)),
            round(outcome.probability, 10),
        )
        for outcome in transition.distribution.outcomes
    )
    assert branches == [
        ((), 0.75),
        (("TAROT",), 0.25),
    ]
    assert "8 Ball x1" in transition.distribution.random_sources


def test_oops_all_sixes_doubles_eight_ball_probability():
    eight = BalatroCard("8", "Hearts")
    state = _state(
        [eight],
        [EightBallJoker(), OopsAll6sJoker()],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5,
        ("TAROT",): 0.5,
    }


def test_red_seal_retrigger_gives_eight_ball_two_independent_attempts():
    eight = BalatroCard("8", "Hearts", seal="Red")
    state = _state([eight], [EightBallJoker()], consumable_slots=1)

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5625,
        ("TAROT",): 0.4375,
    }
    assert "8 Ball x2" in transition.distribution.random_sources


def test_two_eight_ball_attempts_can_fill_two_slots():
    eight = BalatroCard("8", "Hearts", seal="Red")
    state = _state([eight], [EightBallJoker()], consumable_slots=2)

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5625,
        ("TAROT",): 0.375,
        ("TAROT", "TAROT"): 0.0625,
    }


def test_blueprint_copy_of_eight_ball_adds_independent_attempt():
    eight = BalatroCard("8", "Hearts")
    state = _state(
        [eight],
        [BlueprintJoker(), EightBallJoker()],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5625,
        ("TAROT",): 0.4375,
    }
    assert "8 Ball x2" in transition.distribution.random_sources


def test_eight_ball_uses_slot_before_main_seance_generation():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(
        cards,
        [EightBallJoker(), SeanceJoker()],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        ("SPECTRAL",): 0.75,
        ("TAROT",): 0.25,
    }


def test_live_hand_evaluator_routes_through_generated_consumable_projection():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(cards, [SeanceJoker()])
    evaluator = LiveHandDecisionEvaluator()

    projection = evaluator.project_play(
        state,
        BalatroAction(PLAY_CARDS, cards),
    )

    assert projection.joker_projection_complete is True
    assert projection.unsupported_jokers == ()
    assert any(
        _generated_categories(outcome) == ["SPECTRAL"]
        for outcome in projection.outcomes
    )
