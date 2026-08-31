from __future__ import annotations

from types import SimpleNamespace

from games.balatro.aces_dna_hand_policy import _dna_aces_fit
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.boss_hand_constraint_policy import _mouth_discard_fit
from games.balatro.held_round_end_resource_policy import _blue_reward_count
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    LiveBlindPlan,
    LiveBlindPlanValue,
)
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
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


def _blue_seal_projection_owns_production_planner() -> SemanticCheck:
    blue = SimpleNamespace(seal="Blue", debuffed=False)
    ordinary = SimpleNamespace(seal=None, debuffed=False)
    state = SimpleNamespace(consumable_slots=2, consumables=())
    reward_count = _blue_reward_count(state, (blue, ordinary))
    base_native = (
        getattr(LiveBlindClearPlanner._terminal_value, "__module__", "")
        == "games.balatro.live.blind_clear_planner"
        and hasattr(LiveBlindClearPlanner, "_held_round_end_consumables")
    )
    production_inherits_native = issubclass(D1LiveBlindClearPlanner, LiveBlindClearPlanner)
    retired_sentinel_absent = not hasattr(
        D1LiveBlindClearPlanner,
        "_held_round_end_resource_policy_installed",
    )
    passed = (
        reward_count == 1
        and base_native
        and production_inherits_native
        and retired_sentinel_absent
    )
    return SemanticCheck(
        passed,
        observed=(
            f"reward_count={reward_count}, base_native={base_native}, "
            f"production_inherits_native={production_inherits_native}, "
            f"retired_sentinel_absent={retired_sentinel_absent}"
        ),
        expected="one Blue reward with native planner ownership and no held-resource installer sentinel",
        detail=(
            "Blue-Seal round-end generation belongs to the canonical live planner and must "
            "remain available to the integrated production D1 planner without package-time mutation"
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


def _discard_prefilter_keeps_wide_redraws() -> SemanticCheck:
    hand = [
        SimpleNamespace(rank=rank, suit=suit, enhancement=None, edition=None, seal=None)
        for rank, suit in (
            ("A", "Hearts"), ("K", "Spades"), ("Q", "Clubs"), ("J", "Diamonds"),
            ("10", "Hearts"), ("8", "Spades"), ("6", "Clubs"), ("3", "Diamonds"),
        )
    ]
    state = SimpleNamespace(hand=hand)
    actions = [BalatroAction(DISCARD_CARDS, cards=[card]) for card in hand]
    actions.extend(
        BalatroAction(DISCARD_CARDS, cards=[hand[index], hand[(index + 1) % len(hand)]])
        for index in range(len(hand))
    )
    actions.extend(
        (
            BalatroAction(DISCARD_CARDS, cards=hand[:4]),
            BalatroAction(DISCARD_CARDS, cards=hand[4:]),
            BalatroAction(DISCARD_CARDS, cards=hand[:5]),
        )
    )

    planner = LiveBlindClearPlanner()
    filtered = planner._prefilter_discards(state, actions, limit=4)
    widths = tuple(len(tuple(action.cards or ())) for action in filtered)
    passed = len(filtered) == 4 and max(widths, default=0) >= 4
    return SemanticCheck(
        passed,
        observed=f"discard_widths={widths}",
        expected="bounded four-candidate beam contains at least one 4+ card redraw",
        detail=(
            "cheap retained-structure prefiltering must not make D1's projected discard beam "
            "singleton-only; full-blind projection still chooses among the preserved candidates"
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
        "d1.resources.blue_seal_production_owner",
        "D1_SURVIVAL",
        "Blue-Seal round-end generation must remain native to the production D1 planner.",
        _blue_seal_projection_owns_production_planner,
        source="Phase-0 consolidation: held-resource installer retirement",
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
    SemanticBenchmarkCase(
        "d1.search.discard_width_reserve",
        "D1_SURVIVAL",
        "Bounded D1 search must preserve efficient multi-card redraw candidates.",
        _discard_prefilter_keeps_wide_redraws,
        source="Live three-run gate: repeated singleton discard exhaustion",
    ),
)
