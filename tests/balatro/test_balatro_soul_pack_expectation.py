from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.build.soul_expectation import SoulExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _BuildValue:
    VALUES = {
        "CanioJoker": 1.0,
        "ChicotJoker": 2.0,
        "PerkeoJoker": 3.0,
        "TribouletJoker": 4.0,
        "YorickJoker": 5.0,
    }

    def evaluate(self, state, joker):
        return SimpleNamespace(total_gain=self.VALUES[type(joker).__name__])


class _SoulTarget:
    def can_use(self, context):
        return len(context.state.jokers) < context.state.joker_slots


class _SoulExpectation:
    available = True
    complete = True
    expected_build_gain = 6.25
    rationale = ("modeled legendary expectation",)


class _SoulEvaluator:
    def evaluate(self, state):
        return _SoulExpectation()


def test_soul_expectation_averages_modeled_legendary_build_values():
    state = BalatroState()
    result = SoulExpectationEvaluator(build_value=_BuildValue()).evaluate(state)

    assert result.available
    assert result.complete
    assert result.expected_build_gain == 3.0
    assert [outcome.joker_name for outcome in result.outcomes] == [
        "CanioJoker",
        "ChicotJoker",
        "PerkeoJoker",
        "TribouletJoker",
        "YorickJoker",
    ]


def test_soul_expectation_fails_closed_without_joker_capacity():
    state = BalatroState()
    state.jokers = [object()] * state.joker_slots

    result = SoulExpectationEvaluator(build_value=_BuildValue()).evaluate(state)

    assert not result.available
    assert result.complete
    assert result.expected_build_gain == 0.0


def test_pack_soul_uses_modeled_expectation_not_ante_bonus():
    state = BalatroState()
    state.ante = 1
    policy = BalatroPackPolicy()
    policy.soul_evaluator = _SoulEvaluator()
    action = BalatroAction(SELECT_PACK_CARD, target=object())

    score = policy._score_soul(state, action, _SoulTarget())

    assert score.total == 6.25
    assert any("current-build expectation" in note for note in score.notes)
    assert not any("early-Ante" in note for note in score.notes)
