from __future__ import annotations

from types import SimpleNamespace

from games.balatro.bond_power_engine_retention_policy import (
    _best_material_projected_engine,
    _raw_replacement_delta,
)


def _bond(bond_id: str, *, rank_value: int, realization: str) -> dict:
    return {
        "bond_id": bond_id,
        "rank_value": rank_value,
        "realization": realization,
    }


def test_preexisting_strong_engine_does_not_justify_destroying_another_engine():
    current = {
        "relevant_bonds": (
            _bond("held_cards", rank_value=2, realization="ACTIVE"),
            _bond("cash", rank_value=1, realization="ACTIVE"),
        )
    }
    projected = {
        "relevant_bonds": (
            _bond("held_cards", rank_value=2, realization="ACTIVE"),
            _bond("pair", rank_value=1, realization="PARTIAL"),
        )
    }

    engine, strength, gain = _best_material_projected_engine(current, projected)

    assert engine == "pair"
    assert strength == 1.5
    assert gain == 1.5


def test_material_projected_engine_requires_actual_replacement_created_gain():
    current = {
        "relevant_bonds": (
            _bond("held_cards", rank_value=2, realization="ACTIVE"),
        )
    }
    projected = {
        "relevant_bonds": (
            _bond("held_cards", rank_value=3, realization="MATURE"),
        )
    }

    engine, strength, gain = _best_material_projected_engine(current, projected)

    assert engine == "held_cards"
    assert strength == 4.5
    assert gain == 1.5


def test_raw_replacement_delta_excludes_bond_transition_bonus():
    incumbent = SimpleNamespace(fixture_role="incumbent")
    candidate = SimpleNamespace(fixture_role="candidate")
    state = SimpleNamespace(jokers=[SimpleNamespace(fixture_role="other"), incumbent], money=20)

    class _Evaluator:
        def evaluate(self, baseline, joker):
            del baseline
            return SimpleNamespace(
                total_gain=2.00
                if getattr(joker, "fixture_role", None) == "incumbent"
                else 0.78
            )

    policy = SimpleNamespace(
        transition_planner=SimpleNamespace(evaluator=_Evaluator()),
        _economics=lambda _state, _candidate, **_kwargs: SimpleNamespace(money_after=17),
    )

    delta = _raw_replacement_delta(policy, state, candidate, 1)

    assert delta == -1.22
    # The helper recomputes the mechanical candidate/incumbent values on the same
    # post-transaction baseline; a later Bond-transition bonus is not part of it.
