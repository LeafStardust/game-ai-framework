import pytest

from games.balatro.build.wheel_expectation import WheelExpectation
from games.balatro.live.consumable_timing import HOLD, USE, LiveConsumableTimingPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import Fool, WheelOfFortune


class _Blind:
    requirement = 1000


class _WheelEvaluator:
    def __init__(self, result: WheelExpectation):
        self.result = result
        self.calls = 0

    def evaluate(self, state):
        self.calls += 1
        return self.result


def _expectation(
    *,
    available=True,
    complete=True,
    eligible=(0,),
    probability=0.25,
    conditional_gain=2.0,
    expected_gain=0.5,
):
    return WheelExpectation(
        available=available,
        complete=complete,
        eligible_indices=tuple(eligible),
        success_probability=float(probability),
        conditional_build_gain=float(conditional_gain),
        expected_build_gain=float(expected_gain),
        rationale=("fixture analytic Wheel expectation",),
    )


def _state(consumables, *, slots=2):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.consumables = list(consumables)
    state.consumable_slots = slots
    state.hands_remaining = 3
    state.score = 0
    state.blind = _Blind()
    return state


def test_held_wheel_uses_when_exactly_one_editionless_target_is_eligible():
    wheel = WheelOfFortune()
    state = _state([wheel])
    evaluator = _WheelEvaluator(_expectation(eligible=(1,), expected_gain=0.75))

    recommendation = LiveConsumableTimingPolicy(
        wheel_evaluator=evaluator,
    ).recommend(state, wheel)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.before_projection is None
    assert recommendation.after_projection is None
    assert recommendation.immediate_gain == pytest.approx(0.75)
    assert evaluator.calls == 1
    assert any("exactly one editionless Joker" in note for note in recommendation.rationale)
    assert any("no RNG sample or seed read" in note for note in recommendation.rationale)

    action = recommendation.to_action()
    assert action is not None
    assert action.target is wheel
    assert action.cards == []


def test_held_wheel_holds_with_multiple_targets_and_no_pressure():
    wheel = WheelOfFortune()
    state = _state([wheel], slots=2)
    evaluator = _WheelEvaluator(
        _expectation(eligible=(0, 2), probability=0.25, expected_gain=0.6)
    )

    recommendation = LiveConsumableTimingPolicy(
        wheel_evaluator=evaluator,
    ).recommend(state, wheel)

    assert recommendation.decision == HOLD
    assert recommendation.immediate_gain == pytest.approx(0.6)
    assert recommendation.to_action() is None
    assert any("multiple editionless Jokers" in note for note in recommendation.rationale)


def test_held_wheel_uses_with_multiple_targets_when_slots_are_full():
    wheel = WheelOfFortune()
    filler = Fool()
    state = _state([wheel, filler], slots=2)
    evaluator = _WheelEvaluator(
        _expectation(eligible=(0, 1), probability=0.25, expected_gain=0.4)
    )

    recommendation = LiveConsumableTimingPolicy(
        wheel_evaluator=evaluator,
    ).recommend(state, wheel)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.immediate_gain == pytest.approx(0.4)
    assert any("consumable slots are full" in note for note in recommendation.rationale)


def test_held_wheel_uses_when_public_probability_modifiers_guarantee_success():
    wheel = WheelOfFortune()
    state = _state([wheel], slots=3)
    evaluator = _WheelEvaluator(
        _expectation(eligible=(0, 1), probability=1.0, expected_gain=1.5)
    )

    recommendation = LiveConsumableTimingPolicy(
        wheel_evaluator=evaluator,
    ).recommend(state, wheel)

    assert recommendation.decision == USE
    assert recommendation.immediate_gain == pytest.approx(1.5)
    assert any("effectively guaranteed" in note for note in recommendation.rationale)


@pytest.mark.parametrize(
    "result, expected_note",
    [
        (
            _expectation(
                available=False,
                eligible=(),
                conditional_gain=0.0,
                expected_gain=0.0,
            ),
            "no editionless public Joker target",
        ),
        (
            _expectation(complete=False, expected_gain=0.0),
            "expectation is incomplete",
        ),
        (
            _expectation(expected_gain=0.0),
            "no positive modeled expected build gain",
        ),
    ],
)
def test_held_wheel_fails_closed_when_expectation_is_not_actionable(
    result,
    expected_note,
):
    wheel = WheelOfFortune()
    state = _state([wheel])

    recommendation = LiveConsumableTimingPolicy(
        wheel_evaluator=_WheelEvaluator(result),
    ).recommend(state, wheel)

    assert recommendation.decision == HOLD
    assert recommendation.target is None
    assert recommendation.to_action() is None
    assert expected_note in recommendation.rationale[0]


def test_fool_reuses_held_wheel_timing_without_chaining_wheel_execution():
    fool = Fool()
    state = _state([fool], slots=1)
    state.last_tarot_planet = "c_wheel_of_fortune"
    evaluator = _WheelEvaluator(_expectation(eligible=(0,), expected_gain=0.8))

    recommendation = LiveConsumableTimingPolicy(
        wheel_evaluator=evaluator,
    ).recommend(state, fool)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert evaluator.calls == 1
    assert any("Wheel of Fortune" in note for note in recommendation.rationale)
    assert any("fresh observation" in note for note in recommendation.rationale)

    action = recommendation.to_action()
    assert action is not None
    assert action.target is fool
    assert action.cards == []
