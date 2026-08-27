from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_build_policy import BuildAwareLiveHandActionPolicy
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


class RideTheBusJoker:
    def __init__(self, mult: int = 5) -> None:
        self.mult = mult
        self.debuffed = False


class _HandEvaluator:
    def evaluate(self, cards, *, rules=None):
        return SimpleNamespace(value="HIGH_CARD")

    def scoring_cards(self, hand, cards, *, rules=None):
        return list(cards)


def _plan(action, *, consumables: float) -> LiveBlindPlan:
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=1.0,
            expected_progress=1.0,
            expected_score=100.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
            expected_consumables=consumables,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )


def _terminal_resource_hierarchy() -> SemanticCheck:
    face = SimpleNamespace(rank="J", enhancement=None, debuffed=False)
    numbered = SimpleNamespace(rank="9", enhancement=None, debuffed=False)
    state = SimpleNamespace(
        jokers=[RideTheBusJoker(5)],
        boss_name="",
        boss_blind_only_hand=None,
    )

    policy = object.__new__(BuildAwareLiveHandActionPolicy)
    policy._ranking_state = state
    policy._hand_evaluator = _HandEvaluator()
    policy._preservation = lambda plan: 0.0

    bus_preserving = _plan(
        BalatroAction(PLAY_CARDS, cards=[numbered]),
        consumables=0.0,
    )
    resource_preserving = _plan(
        BalatroAction(PLAY_CARDS, cards=[face]),
        consumables=1.0,
    )
    equal_resource_face = _plan(
        BalatroAction(PLAY_CARDS, cards=[face]),
        consumables=0.0,
    )

    bus_key = policy._safe_equivalent_clear_key(bus_preserving)
    resource_key = policy._safe_equivalent_clear_key(resource_preserving)
    equal_face_key = policy._safe_equivalent_clear_key(equal_resource_face)

    passed = resource_key > bus_key > equal_face_key
    return SemanticCheck(
        passed,
        observed=(
            f"resource_vs_bus={resource_key > bus_key}, "
            f"bus_vs_overkill={bus_key > equal_face_key}"
        ),
        expected="generated resources outrank Bus preservation; Bus outranks equal-resource overkill",
        detail=(
            "terminal guaranteed-clear ordering must not save Ride the Bus by sacrificing "
            "a Blue-Seal reward, but may save the stack when round resources are otherwise equal"
        ),
    )


RED_WHITE_D1_RESOURCE_CASES = (
    SemanticBenchmarkCase(
        "d1.resources.bus_terminal_hierarchy",
        "D1_SURVIVAL",
        "Equivalent terminal clears preserve round-end resources before Ride the Bus stack.",
        _terminal_resource_hierarchy,
        source="Phase-0 consolidation: retired ride_the_bus_execution_policy selector",
    ),
)
