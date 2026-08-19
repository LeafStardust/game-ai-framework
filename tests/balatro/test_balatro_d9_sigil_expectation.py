from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build.sigil_expectation import (
    SigilExpectation,
    SigilExpectationEvaluator,
)
from games.balatro.card import BalatroCard
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _Profiler:
    def profile(self, state):
        return object()


class _SuitCardEvaluator:
    VALUES = {
        "Hearts": 4.0,
        "Diamonds": 0.0,
        "Clubs": 0.0,
        "Spades": 0.0,
    }

    def evaluate(self, state, *, suit=None, **kwargs):
        return SimpleNamespace(total_gain=self.VALUES.get(str(suit), 0.0))


class _SigilEvaluator:
    def __init__(self, expectation: SigilExpectation):
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
            "label": "Sigil",
            "ability_name": "Sigil",
            "ability_set": "Spectral",
        },
    )


def _rank(state: BalatroState, expectation: SigilExpectation):
    policy = BalatroPackPolicy(
        skip_bias=0.35,
        sigil_evaluator=_SigilEvaluator(expectation),
    )
    return policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=_choice()),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


def test_d9_sigil_expectation_enumerates_four_suit_branches_without_rng():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Clubs"),
    ]
    evaluator = SigilExpectationEvaluator(
        profiler=_Profiler(),
        card_evaluator=_SuitCardEvaluator(),
    )

    result = evaluator.evaluate(state)

    assert result.available
    assert result.complete
    assert result.expected_total_gain == 2.0
    assert any("Hearts B6 rewrite gain=8.000" in note for note in result.rationale)
    assert any("expected B6 Sigil rewrite gain=2.000" in note for note in result.rationale)


def test_d9_sigil_positive_expectation_can_beat_explicit_skip():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [BalatroCard("K", "Hearts")]
    expectation = SigilExpectation(
        available=True,
        complete=True,
        expected_contextual_gain=0.8,
        expected_total_gain=0.8,
        rationale=("stub positive Sigil expectation",),
    )

    ranked = _rank(state, expectation)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.cards == []
    assert ranked[0].total > 0.35
    assert any("Sigil uses analytic public-state expectation" in note for note in ranked[0].notes)
    assert any("B6 Sigil expected rewrite gain=0.800" in note for note in ranked[0].notes)


def test_d9_sigil_nonpositive_expectation_fails_closed_below_skip():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [BalatroCard("K", "Hearts")]
    expectation = SigilExpectation(
        available=True,
        complete=True,
        expected_contextual_gain=-0.2,
        expected_total_gain=-0.2,
        rationale=("stub negative Sigil expectation",),
    )

    ranked = _rank(state, expectation)

    assert ranked[0].action.name == SKIP_BOOSTER
    sigil = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert sigil.total == -1.0
    assert any("Sigil has no positive analytic rewrite value" in note for note in sigil.notes)
