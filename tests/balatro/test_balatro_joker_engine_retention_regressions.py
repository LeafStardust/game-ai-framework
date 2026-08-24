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
            # This engine was already strong before the hypothetical replacement.
            _bond("held_cards", rank_value=2, realization="ACTIVE"),
            # The replacement only creates a small unrelated Pair foothold.
            _bond("pair", rank_value=1, realization="PARTIAL"),
        )
    }

    engine, strength, gain = _best_material_projected_engine(current, projected)

    assert engine == "pair"
    assert strength == 1.5
    assert gain == 1.5
    # held_cards must not be returned merely because it remains the strongest
    # absolute engine after the sale. That was the Attempt-3 Bull failure mode.


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
    option = SimpleNamespace(replace_index=1, build_delta=-1.22)
    transition = SimpleNamespace(alternatives=(option,))
    policy = SimpleNamespace(
        transition_planner=SimpleNamespace(plan=lambda state, candidate: transition)
    )

    delta = _raw_replacement_delta(policy, object(), object(), 1)

    assert delta == -1.22
    # A later Bond-transition bonus must not mutate this common-baseline result.
    # This is the exact Cavendish -> Even Steven failure mechanism from Attempt 3.
