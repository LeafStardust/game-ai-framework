from types import SimpleNamespace

import pytest

import games.balatro.joker_policy as joker_policy
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import JokerAcquisitionPolicy, _bond_transition_bonus
from games.balatro.state import BalatroState


class DummyJoker(Joker):
    def __init__(self, native_gain=0.0):
        super().__init__()
        self.native_gain = float(native_gain)

    def apply(self, context: JokerContext) -> JokerContext:
        return context


class FixedNativeEvaluator:
    """Deterministic mechanical evaluator for the installed post-transaction owner."""

    def evaluate(self, state, joker):
        del state
        return SimpleNamespace(total_gain=float(joker.native_gain))


def _policy_with_native_values() -> JokerAcquisitionPolicy:
    planner = SimpleNamespace(evaluator=FixedNativeEvaluator())
    return JokerAcquisitionPolicy(transition_planner=planner)


def test_joker_transition_uses_canonical_strategy_delta_and_domain_projection(monkeypatch):
    state = BalatroState()
    incumbent = DummyJoker()
    candidate = DummyJoker()
    state.jokers = [incumbent]
    observed = {}

    def fake_delta(current, projected):
        observed["current"] = current
        observed["projected"] = projected
        return SimpleNamespace(value=10.0, raw_delta=12.0, transition_cost=2.0)

    monkeypatch.setattr(joker_policy, "strategy_delta_from_states", fake_delta)

    adjustment, notes = _bond_transition_bonus(state, candidate, replace_index=0)

    assert observed["current"] is state
    assert observed["projected"] is not state
    assert observed["projected"].jokers == [candidate]
    assert state.jokers == [incumbent]
    assert adjustment == 1.0
    assert any("canonical StrategyDelta" in note for note in notes)
    assert any("weighted strategic adjustment" in note for note in notes)


def test_joker_add_scoring_preserves_post_transaction_native_gain_and_adds_strategy_delta():
    state = BalatroState()
    state.money = 20
    candidate = DummyJoker(native_gain=2.0)
    policy = _policy_with_native_values()

    strategy_adjustment, _ = _bond_transition_bonus(state, candidate)
    # The installed post-transaction authority intentionally recomputes this term
    # through its evaluator rather than trusting this stale pre-transaction value.
    option = policy._score_add(state, candidate, 999.0)

    assert option.build_gain == pytest.approx(2.0 + strategy_adjustment)
    assert option.total_advantage == pytest.approx(
        option.build_gain + option.economics.total_adjustment
    )
    assert any("post-transaction whole-build candidate gain=2.000" in note for note in option.rationale)
    assert any("StrategyDelta" in note for note in option.rationale)


def test_joker_replacement_preserves_post_transaction_native_delta_and_adds_strategy_delta():
    state = BalatroState()
    state.money = 20
    incumbent = DummyJoker(native_gain=1.0)
    candidate = DummyJoker(native_gain=5.0)
    state.jokers = [incumbent]
    policy = _policy_with_native_values()
    replacement = SimpleNamespace(
        replace_index=0,
        # The installed owner recomputes 5 - 1 = 4 from the resulting state.
        build_delta=999.0,
        eligible=True,
        blocked_reason=None,
        rationale=("native mechanical replacement",),
    )

    strategy_adjustment, _ = _bond_transition_bonus(state, candidate, replace_index=0)
    option = policy._score_replacement(state, candidate, replacement)

    assert option.build_gain == pytest.approx(4.0 + strategy_adjustment)
    assert option.eligible
    assert "native mechanical replacement" in option.rationale
    assert any("post-transaction raw replacement delta=4.000" in note for note in option.rationale)
    assert any("StrategyDelta" in note for note in option.rationale)


def test_joker_policy_no_longer_imports_legacy_strategy_composition_authority():
    source_names = set(joker_policy.__dict__)
    assert "evaluate_bond_composition" not in source_names
    assert "StrategyCommitment" not in source_names
    assert "BondRank" not in source_names
