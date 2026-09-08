from __future__ import annotations

from copy import copy
from types import SimpleNamespace

import pytest

from games.balatro.reroll_tarot_guard_policy import (
    RerollTarotExpectationEvaluator,
    _MAX_EVALUATED_RECORDS_LARGE_POOL,
    _bounded_record_indices,
)


class _State(SimpleNamespace):
    def copy(self):
        return copy(self)


def _state(record_count: int) -> _State:
    return _State(
        consumable_generation_pool_observed=True,
        consumable_generation_pools={
            "TAROT": [
                {
                    "ability_name": f"Tarot {index}",
                    "ability_set": "TAROT",
                    "center": f"c_test_{index}",
                    "label": f"Tarot {index}",
                }
                for index in range(record_count)
            ]
        },
        money=20,
    )


def test_small_public_tarot_pool_keeps_every_outcome_exact():
    assert _bounded_record_indices(6, exact=True) == tuple(range(6))


def test_large_public_tarot_pool_uses_stable_spread_budget():
    indices = _bounded_record_indices(22, exact=False)

    assert len(indices) == _MAX_EVALUATED_RECORDS_LARGE_POOL
    assert indices == tuple(sorted(set(indices)))
    assert indices[0] == 0
    assert indices[-1] == 21


def test_large_public_tarot_pool_keeps_omitted_mass_at_zero(monkeypatch):
    evaluator = RerollTarotExpectationEvaluator()
    created = []
    evaluated = []

    def create(record):
        created.append(record["center"])
        return SimpleNamespace(name=record["label"], category="TAROT", price=0)

    def evaluate(_state, candidate):
        evaluated.append(candidate.name)
        return SimpleNamespace(complete=True, expected_gain=1.0)

    monkeypatch.setattr(evaluator.factory, "create", create)
    monkeypatch.setattr(evaluator.held_option, "evaluate", evaluate)

    result = evaluator.evaluate(_state(22), money=20, expected_price=3)

    assert result.complete is True
    assert result.outcome_count == 22
    assert len(created) == 22
    assert len(evaluated) == _MAX_EVALUATED_RECORDS_LARGE_POOL
    assert result.expected_option_gain == pytest.approx(
        _MAX_EVALUATED_RECORDS_LARGE_POOL / 22.0
    )


def test_large_public_tarot_pool_preflights_unevaluated_records(monkeypatch):
    evaluator = RerollTarotExpectationEvaluator()
    calls = 0

    def create(record):
        nonlocal calls
        calls += 1
        if record["center"] == "c_test_21":
            return None
        return SimpleNamespace(name=record["label"], category="TAROT", price=0)

    monkeypatch.setattr(evaluator.factory, "create", create)

    result = evaluator.evaluate(_state(22), money=20, expected_price=3)

    assert result.complete is False
    assert result.expected_option_gain == 0.0
    assert calls == 22
    assert "not modeled" in result.rationale[0]
