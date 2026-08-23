from __future__ import annotations

from types import SimpleNamespace

import games.balatro.pinned_strategy_retention_policy as retention
from games.balatro.bonds.strategy_semantics import StrategyCandidate, StrategyCommitment
from games.balatro.joker_policy import HOLD, REPLACE, JokerAcquisitionDecision, JokerAcquisitionThresholds
from games.balatro.pinned_strategy_transition_policy import _strategy_transition_gain


def _strategy(strategy_id: str, *, commitment=StrategyCommitment.PINNED, confidence=0.7, strength=10.0):
    return StrategyCandidate(
        strategy_id=strategy_id,
        bond_ids=("a", "b"),
        sources=("A", "B"),
        roles=(),
        links=(),
        motif_ids=(),
        commitment=commitment,
        confidence=confidence,
        strength=strength,
        prescriptions=(),
    )


def _composition(candidate=None):
    return SimpleNamespace(
        pinned_strategy_id=None if candidate is None else candidate.strategy_id,
        strategy_candidates=() if candidate is None else (candidate,),
    )


def _replace_decision():
    selected = SimpleNamespace(replace_index=0)
    return JokerAcquisitionDecision(
        action=REPLACE,
        candidate="Candidate",
        selected=selected,
        options=(selected,),
        thresholds=JokerAcquisitionThresholds(),
        rationale=("lower layer chose replacement",),
    )


def test_strategy_transition_rewards_newly_pinned_engine():
    after = _strategy("engine", commitment=StrategyCommitment.PINNED, confidence=0.75, strength=12.0)
    gain, notes = _strategy_transition_gain(_composition(), _composition(after))
    assert gain > 0.0
    assert any("forms pinned strategy engine" in note for note in notes)


def test_strategy_transition_rewards_commitment_advance():
    before = _strategy("engine", commitment=StrategyCommitment.PINNED, strength=10.0)
    after = _strategy("engine", commitment=StrategyCommitment.ESTABLISHED, strength=12.0)
    gain, notes = _strategy_transition_gain(_composition(before), _composition(after))
    assert gain > 0.0
    assert any("PINNED->ESTABLISHED" in note for note in notes)


def test_replacement_is_held_when_it_removes_current_pinned_strategy(monkeypatch):
    current = _strategy("engine", strength=12.0)
    states = iter((((), _composition(current)), ((), _composition())))
    monkeypatch.setattr(retention, "evaluate_bond_composition", lambda state: next(states))
    monkeypatch.setattr(retention, "projected_state_with_jokers", lambda state, jokers: SimpleNamespace())
    decision = retention.apply_pinned_strategy_retention(
        SimpleNamespace(jokers=[object()]), object(), _replace_decision()
    )
    assert decision.action == HOLD
    assert decision.selected is None
    assert any("pinned strategy retention" in note for note in decision.rationale)


def test_replacement_remains_allowed_when_same_pinned_strategy_survives(monkeypatch):
    current = _strategy("engine", strength=12.0)
    projected = _strategy("engine", strength=11.0)
    states = iter((((), _composition(current)), ((), _composition(projected))))
    monkeypatch.setattr(retention, "evaluate_bond_composition", lambda state: next(states))
    monkeypatch.setattr(retention, "projected_state_with_jokers", lambda state, jokers: SimpleNamespace())
    original = _replace_decision()
    decision = retention.apply_pinned_strategy_retention(
        SimpleNamespace(jokers=[object()]), object(), original
    )
    assert decision.action == REPLACE
    assert decision.selected is original.selected


def test_materially_stronger_new_pinned_strategy_can_replace_old_one(monkeypatch):
    current = _strategy("engine-a", strength=10.0)
    projected = _strategy("engine-b", strength=13.0)
    states = iter((((), _composition(current)), ((), _composition(projected))))
    monkeypatch.setattr(retention, "evaluate_bond_composition", lambda state: next(states))
    monkeypatch.setattr(retention, "projected_state_with_jokers", lambda state, jokers: SimpleNamespace())
    decision = retention.apply_pinned_strategy_retention(
        SimpleNamespace(jokers=[object()]), object(), _replace_decision()
    )
    assert decision.action == REPLACE
    assert any("pinned strategy pivot allowed" in note for note in decision.rationale)
