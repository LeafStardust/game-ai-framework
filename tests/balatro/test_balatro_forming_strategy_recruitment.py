from types import SimpleNamespace

import games.balatro  # install package-level authorities
import games.balatro.strategy_plan_pack_policy as pack_goal_module
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.strategy_plan import StrategyBondGoal, StrategyPlan
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.strategy_authority_correction_policy import _component_match


def _goal(bond_id: str, priority: float) -> StrategyBondGoal:
    return StrategyBondGoal(
        bond_id=bond_id,
        rank=BondRank.R1,
        next_rank=BondRank.R2,
        contribution=5.0,
        next_rank_threshold=9.0,
        points_to_next_rank=4.0,
        priority=priority,
    )


def _plan(*, missing, goals, commitment=StrategyCommitment.FORMING):
    return StrategyPlan(
        strategy_id="test_strategy",
        commitment=commitment,
        confidence=0.5,
        strength=5.0,
        core_sources=("CORE",),
        bond_goals=tuple(goals),
        missing_features=(),
        present_components=("CORE",),
        missing_components=tuple(missing),
        prescriptions=tuple(f"seek_component:{value}" for value in missing),
        completion=0.25,
    )


def test_leveling_support_recognizes_direct_joker_providers():
    plan = _plan(missing=("LEVELING_SUPPORT",), goals=())

    assert _component_match(plan, SimpleNamespace(name="Space Joker")) == "LEVELING_SUPPORT"
    assert _component_match(plan, SimpleNamespace(name="Blueprint")) == "LEVELING_SUPPORT"
    assert _component_match(plan, SimpleNamespace(name="Brainstorm")) == "LEVELING_SUPPORT"


def test_infrastructure_does_not_alias_to_unrelated_named_joker():
    plan = _plan(missing=("STEEL_INFRASTRUCTURE",), goals=())

    assert _component_match(plan, SimpleNamespace(name="Steel Joker")) is None


def test_forming_burnt_plan_can_seek_only_target_hand_planet_goal():
    plan = _plan(
        missing=("TARGET_HAND_LEVEL", "LEVELING_SUPPORT"),
        goals=(
            _goal("burnt", 10.0),
            _goal("high_card", 9.0),
            _goal("cash", 8.0),
        ),
    )

    assert pack_goal_module._goal_ids(plan) == ("high_card",)


def test_forming_baron_plan_can_seek_king_and_steel_infrastructure_only():
    plan = _plan(
        missing=("KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE"),
        goals=(
            _goal("held_cards", 10.0),
            _goal("kings", 9.0),
            _goal("steel", 8.0),
        ),
    )

    assert pack_goal_module._goal_ids(plan) == ("kings", "steel")


def test_forming_exact_missing_joker_does_not_gain_unrelated_pack_authority():
    plan = _plan(
        missing=("MIME",),
        goals=(_goal("held_cards", 10.0), _goal("kings", 9.0)),
    )

    assert pack_goal_module._goal_ids(plan) == ()


def test_pinned_plan_retains_normal_pack_goals():
    plan = _plan(
        missing=("KING_INFRASTRUCTURE",),
        goals=(_goal("held_cards", 10.0), _goal("kings", 9.0)),
        commitment=StrategyCommitment.PINNED,
    )

    assert pack_goal_module._goal_ids(plan) == ("held_cards", "kings")
