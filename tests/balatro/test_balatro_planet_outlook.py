from games.balatro.card import BalatroCard
from games.balatro.planet_outlook import PlanetOutlookEvaluator
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState


_RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
_SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")


def _standard_deck():
    return [BalatroCard(rank, suit) for suit in _SUITS for rank in _RANKS]


def _state() -> BalatroState:
    state = BalatroState()
    state.owned_deck = _standard_deck()
    state.hand_size = 8
    return state


def test_standard_deck_suppresses_speculative_straight_flush_planet():
    state = _state()
    evaluator = PlanetOutlookEvaluator()

    mercury = evaluator.evaluate(state, create_planet("MERCURY"))
    neptune = evaluator.evaluate(state, create_planet("NEPTUNE"))

    assert mercury.structural_feasibility > neptune.structural_feasibility
    assert mercury.expected_future_frequency > neptune.expected_future_frequency
    assert mercury.future_value > neptune.future_value
    assert neptune.structural_feasibility < 0.01
    assert neptune.speculative is True


def test_observed_run_history_can_promote_a_demonstrated_straight_flush_line():
    state = _state()
    state.hand_play_counts["STRAIGHT_FLUSH"] = 8
    evaluator = PlanetOutlookEvaluator()

    mercury = evaluator.evaluate(state, create_planet("MERCURY"))
    neptune = evaluator.evaluate(state, create_planet("NEPTUNE"))

    assert neptune.observed_frequency == 1.0
    assert neptune.expected_future_frequency == 1.0
    assert neptune.future_value > mercury.future_value
    assert neptune.speculative is False


def test_planet_outlook_uses_only_unordered_owned_deck_composition():
    state = _state()
    evaluator = PlanetOutlookEvaluator()
    mercury = create_planet("MERCURY")

    before = evaluator.evaluate(state, mercury)
    state.owned_deck = list(reversed(state.owned_deck))
    after = evaluator.evaluate(state, mercury)

    assert after.structural_feasibility == before.structural_feasibility
    assert after.expected_future_frequency == before.expected_future_frequency
    assert after.future_value == before.future_value
