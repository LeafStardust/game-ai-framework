from __future__ import annotations

from types import SimpleNamespace

from games.balatro.aces_dna_hand_policy import _dna_aces_fit
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.boss_hand_constraint_policy import _mouth_discard_fit
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_build_policy import BuildAwareLiveHandActionPolicy
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


class RideTheBusJoker:
    def __init__(self, mult: int = 5) -> None:
        self.mult = mult
        self.debuffed = False


class DNAJoker:
    pass


class ScholarJoker:
    pass


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


def _dna_aces_is_candidate_evidence() -> SemanticCheck:
    ace = SimpleNamespace(rank="A")
    nine = SimpleNamespace(rank="9")
    state = SimpleNamespace(
        jokers=[DNAJoker(), ScholarJoker()],
        round_hand_play_counts={"HIGH_CARD": 0, "PAIR": 0},
    )
    policy = SimpleNamespace(
        _hand_bond_intents=lambda state: (("PAIR", 2.0, "aces"),),
    )

    ace_value, ace_notes = _dna_aces_fit(
        policy,
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
    )
    neutral_value, _ = _dna_aces_fit(
        policy,
        state,
        BalatroAction(PLAY_CARDS, cards=[nine]),
    )
    passed = ace_value > neutral_value and ace_value > 0.0 and bool(ace_notes)
    return SemanticCheck(
        passed,
        observed=f"ace_fit={ace_value:.3f}, neutral_fit={neutral_value:.3f}",
        expected="DNA/Aces setup appears as candidate-specific strategy evidence",
        detail=(
            "duplication/development may distinguish survival-equivalent PLAY candidates "
            "without owning a second post-policy PLAY selector"
        ),
    )


def _mouth_redraw_is_candidate_evidence() -> SemanticCheck:
    cards = [SimpleNamespace(rank=str(rank), suit="Hearts") for rank in range(2, 7)]
    state = SimpleNamespace(
        boss_name="The Mouth",
        boss_blind_only_hand="STRAIGHT",
        jokers=[],
        hand=cards,
    )
    policy = SimpleNamespace(
        _structure_fit=lambda kept, forced, rules=None: 0.5,
    )
    narrow_value, _ = _mouth_discard_fit(
        policy,
        state,
        BalatroAction(DISCARD_CARDS, cards=cards[:1]),
    )
    wide_value, notes = _mouth_discard_fit(
        policy,
        state,
        BalatroAction(DISCARD_CARDS, cards=cards[:4]),
    )
    passed = wide_value > narrow_value > 0.0 and bool(notes)
    return SemanticCheck(
        passed,
        observed=f"narrow_fit={narrow_value:.3f}, wide_fit={wide_value:.3f}",
        expected="locked-Mouth redraw structure and width are discard candidate evidence",
        detail=(
            "The Mouth's exact hand lock remains a mechanics constraint while redraw shaping "
            "stays beneath canonical D1 survival arbitration"
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
    SemanticBenchmarkCase(
        "d1.strategy.dna_aces_evidence",
        "D1_SURVIVAL",
        "DNA/Aces setup must be candidate evidence rather than a post-policy selector.",
        _dna_aces_is_candidate_evidence,
        source="Phase-0 consolidation: aces_dna_hand_policy evidence-only migration",
    ),
    SemanticBenchmarkCase(
        "d1.boss.mouth_redraw_evidence",
        "D1_SURVIVAL",
        "Locked-Mouth redraw shaping must remain candidate evidence beneath boss legality.",
        _mouth_redraw_is_candidate_evidence,
        source="Phase-0 consolidation: boss_hand_constraint_policy post-selector removal",
    ),
)
