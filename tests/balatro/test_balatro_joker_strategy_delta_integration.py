from types import SimpleNamespace

import games.balatro.joker_policy as joker_policy
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import JokerAcquisitionPolicy, _bond_transition_bonus
from games.balatro.state import BalatroState


class DummyJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


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


def test_joker_add_scoring_combines_native_build_gain_with_strategy_delta(monkeypatch):
    state = BalatroState()
    state.money = 20
    candidate = DummyJoker()
    policy = JokerAcquisitionPolicy()

    monkeypatch.setattr(
        joker_policy,
        "_bond_transition_bonus",
        lambda *_args, **_kwargs: (1.25, ("canonical strategy proof",)),
    )

    option = policy._score_add(state, candidate, 2.0)

    assert option.build_gain == 3.25
    assert option.total_advantage == option.build_gain + option.economics.total_adjustment
    assert any("StrategyDelta" in note for note in option.rationale)
    assert any("canonical strategy proof" in note for note in option.rationale)


def test_joker_replacement_strategy_loss_reduces_but_does_not_replace_native_delta(monkeypatch):
    state = BalatroState()
    state.money = 20
    incumbent = DummyJoker()
    candidate = DummyJoker()
    state.jokers = [incumbent]
    policy = JokerAcquisitionPolicy()
    replacement = SimpleNamespace(
        replace_index=0,
        build_delta=4.0,
        eligible=True,
        blocked_reason=None,
        rationale=("native mechanical replacement",),
    )

    monkeypatch.setattr(
        joker_policy,
        "_bond_transition_bonus",
        lambda *_args, **_kwargs: (-1.5, ("canonical strategic loss",)),
    )

    option = policy._score_replacement(state, candidate, replacement)

    assert option.build_gain == 2.5
    assert option.eligible
    assert "native mechanical replacement" in option.rationale
    assert "canonical strategic loss" in option.rationale


def test_joker_policy_no_longer_imports_legacy_strategy_composition_authority():
    source_names = set(joker_policy.__dict__)
    assert "evaluate_bond_composition" not in source_names
    assert "StrategyCommitment" not in source_names
    assert "BondRank" not in source_names
