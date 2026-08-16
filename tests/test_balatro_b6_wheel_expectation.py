import pytest

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build.wheel_expectation import (
    WheelExpectation,
    WheelOfFortuneExpectationEvaluator,
)
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


def _state(jokers):
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.jokers = list(jokers)
    state.joker_slots = 5
    return state


def _wheel_choice():
    return LivePackChoice(
        area_index=0,
        address=0x1234,
        data={
            "area_index": 0,
            "address": 0x1234,
            "live_id": 77,
            "label": "The Wheel of Fortune",
            "ability_name": "The Wheel of Fortune",
            "ability_set": "Tarot",
        },
    )


def test_wheel_expectation_values_only_editionless_public_jokers():
    editionless = EggJoker()
    already_foil = EggJoker()
    already_foil.edition = "FOIL"

    result = WheelOfFortuneExpectationEvaluator().evaluate(
        _state([editionless, already_foil])
    )

    assert result.available is True
    assert result.complete is True
    assert result.eligible_indices == (0,)
    assert result.success_probability == pytest.approx(0.25)
    assert result.conditional_build_gain > 0.0
    assert result.expected_build_gain == pytest.approx(
        result.conditional_build_gain * result.success_probability
    )


def test_wheel_expectation_fails_unavailable_when_every_joker_has_an_edition():
    foil = EggJoker()
    foil.edition = "FOIL"
    poly = EggJoker()
    poly.edition = "POLYCHROME"

    result = WheelOfFortuneExpectationEvaluator().evaluate(_state([foil, poly]))

    assert result.available is False
    assert result.complete is True
    assert result.eligible_indices == ()
    assert result.expected_build_gain == 0.0


def test_oops_all_6s_doubles_wheel_success_probability_without_sampling_rng():
    result = WheelOfFortuneExpectationEvaluator().evaluate(
        _state([EggJoker(), OopsAll6sJoker()])
    )

    assert result.available is True
    assert result.complete is True
    assert result.success_probability == pytest.approx(0.50)
    assert any(
        note == "Oops! All 6s probability multipliers=1"
        for note in result.rationale
    )


def test_two_oops_all_6s_copies_cap_wheel_success_probability_at_one():
    result = WheelOfFortuneExpectationEvaluator().evaluate(
        _state([EggJoker(), OopsAll6sJoker(), OopsAll6sJoker()])
    )

    assert result.success_probability == pytest.approx(1.0)


def test_wheel_expectation_does_not_mutate_authoritative_joker_editions():
    joker = EggJoker()
    state = _state([joker])

    WheelOfFortuneExpectationEvaluator().evaluate(state)

    assert getattr(joker, "edition", None) is None
    assert getattr(state.jokers[0], "edition", None) is None


class _WheelEvaluator:
    def __init__(self, result):
        self.result = result

    def evaluate(self, state):
        return self.result


def test_pack_policy_uses_modeled_wheel_expected_build_gain():
    choice = _wheel_choice()
    result = WheelExpectation(
        available=True,
        complete=True,
        eligible_indices=(0,),
        success_probability=0.25,
        conditional_build_gain=4.0,
        expected_build_gain=1.0,
        rationale=("fixture Wheel expectation",),
    )
    policy = BalatroPackPolicy(wheel_evaluator=_WheelEvaluator(result))

    ranked = policy.rank_actions(
        _state([EggJoker()]),
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total == pytest.approx(1.0)
    assert any("no RNG sample or seed read" in note for note in ranked[0].notes)


def test_pack_policy_skips_wheel_when_no_editionless_target_exists():
    choice = _wheel_choice()
    result = WheelExpectation(
        available=False,
        complete=True,
        eligible_indices=(),
        success_probability=0.25,
        conditional_build_gain=0.0,
        expected_build_gain=0.0,
        rationale=("Wheel has no editionless public Joker target",),
    )
    policy = BalatroPackPolicy(wheel_evaluator=_WheelEvaluator(result))

    ranked = policy.rank_actions(
        _state([]),
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.name == SKIP_BOOSTER
    wheel = next(item for item in ranked if item.action.name == SELECT_PACK_CARD)
    assert wheel.total == -1.0


def test_pack_policy_fails_closed_when_wheel_expectation_is_incomplete():
    choice = _wheel_choice()
    result = WheelExpectation(
        available=True,
        complete=False,
        eligible_indices=(0,),
        success_probability=0.25,
        conditional_build_gain=0.0,
        expected_build_gain=0.0,
        rationale=("fixture incomplete branch",),
    )
    policy = BalatroPackPolicy(wheel_evaluator=_WheelEvaluator(result))

    ranked = policy.rank_actions(
        _state([EggJoker()]),
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.name == SKIP_BOOSTER
    wheel = next(item for item in ranked if item.action.name == SELECT_PACK_CARD)
    assert wheel.total == -1.0
