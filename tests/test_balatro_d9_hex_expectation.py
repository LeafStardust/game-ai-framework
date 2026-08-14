from types import SimpleNamespace

import pytest

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build.hex_expectation import HexExpectation, HexExpectationEvaluator
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _ProbeScorer:
    def score(self, hand, *, state, **kwargs):
        if len(state.jokers) == 2:
            return SimpleNamespace(total=100.0)
        chosen = state.jokers[0]
        total = 140.0 if getattr(chosen, "tag", "") == "good" else 100.0
        return SimpleNamespace(total=total)


class _HexEvaluator:
    def __init__(self, expectation: HexExpectation):
        self.expectation = expectation

    def evaluate(self, state):
        return self.expectation


def _choice() -> LivePackChoice:
    return LivePackChoice(
        area_index=0,
        address=0x1000,
        data={
            "area_index": 0,
            "address": 0x1000,
            "live_id": 500,
            "label": "Hex",
            "ability_name": "Hex",
            "ability_set": "Spectral",
        },
    )


def _rank(state: BalatroState, expectation: HexExpectation):
    return BalatroPackPolicy(
        skip_bias=0.35,
        hex_evaluator=_HexEvaluator(expectation),
    ).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=_choice()),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


def test_d9_hex_expectation_averages_uniform_public_joker_branches():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.jokers = [
        SimpleNamespace(tag="good", edition=None),
        SimpleNamespace(tag="neutral", edition=None),
    ]

    result = HexExpectationEvaluator(scorer=_ProbeScorer()).evaluate(state)

    assert result.available
    assert result.complete
    assert result.branch_count == 2
    assert result.expected_build_gain == pytest.approx(1.2)
    assert any("Joker index 0 B3 Hex branch gain=2.400" in note for note in result.rationale)
    assert any("expected B3 Hex whole-build gain=1.200" in note for note in result.rationale)


def test_d9_hex_positive_expected_whole_build_gain_can_beat_skip():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.jokers = [SimpleNamespace()]
    expectation = HexExpectation(
        available=True,
        complete=True,
        branch_count=1,
        expected_build_gain=1.1,
        rationale=("stub positive Hex expectation",),
    )

    ranked = _rank(state, expectation)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.cards == []
    assert ranked[0].total == 1.1
    assert any("Hex uses analytic B3 whole-build expectation" in note for note in ranked[0].notes)


def test_d9_hex_nonpositive_expected_whole_build_gain_fails_closed():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.jokers = [SimpleNamespace()]
    expectation = HexExpectation(
        available=True,
        complete=True,
        branch_count=1,
        expected_build_gain=-0.4,
        rationale=("stub negative Hex expectation",),
    )

    ranked = _rank(state, expectation)

    assert ranked[0].action.name == SKIP_BOOSTER
    hex_score = next(
        result for result in ranked if result.action.name == SELECT_PACK_CARD
    )
    assert hex_score.total == -1.0
    assert any("Hex has no positive analytic whole-build value" in note for note in hex_score.notes)
