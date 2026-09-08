from __future__ import annotations

"""Phase-3 semantic cases for coherent Red/White build evidence."""

from types import SimpleNamespace

import games.balatro.joker_policy as joker_policy_module
from games.balatro.build.joker_lifecycle import STATEFUL_SCALING
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.joker_policy import JokerAcquisitionPolicy
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.state import BalatroState


def _base_state() -> BalatroState:
    state = BalatroState()
    state.ante = 2
    state.joker_slots = 5
    state.jokers = []
    return state


def _scoring_engine_exposes_direct_score_gain() -> SemanticCheck:
    value = JokerBuildValueEvaluator().evaluate(_base_state(), FlatMultJoker(4))
    passed = value.direct_scoring_gain > 0.0 and value.direct_scoring_value > 0.0
    return SemanticCheck(
        passed,
        observed=(
            f"direct_gain={value.direct_scoring_gain:.6f}, "
            f"direct_value={value.direct_scoring_value:.3f}, "
            f"contextual={value.contextual.total_gain:.3f}"
        ),
        expected="a literal +Mult Joker exposes positive direct-scoring evidence",
        detail=(
            "B3 must identify a real scoring foothold from literal score projection rather than relying "
            "only on structural/Bond labels"
        ),
    )


def _economy_joker_does_not_manufacture_direct_score() -> SemanticCheck:
    value = JokerBuildValueEvaluator().evaluate(_base_state(), GoldenJoker())
    passed = (
        abs(float(value.direct_scoring_gain)) <= 1e-12
        and abs(float(value.direct_scoring_value)) <= 1e-12
        and float(value.contextual.total_gain) > 0.0
    )
    return SemanticCheck(
        passed,
        observed=(
            f"direct_gain={value.direct_scoring_gain:.6f}, "
            f"direct_value={value.direct_scoring_value:.3f}, "
            f"contextual={value.contextual.total_gain:.3f}"
        ),
        expected="an economy-only Joker has zero direct scoring gain but positive contextual value",
        detail=(
            "economy/support evidence may improve build quality, but it must not be converted into chips, "
            "Mult, or fake immediate scoring power"
        ),
    )


def _fresh_scaler_exposes_scaling_potential() -> SemanticCheck:
    value = JokerBuildValueEvaluator().evaluate(_base_state(), RideTheBusJoker())
    scaling = STATEFUL_SCALING in set(value.contextual.descriptor.produces)
    return SemanticCheck(
        scaling and float(value.contextual.total_gain) > 0.0,
        observed=(
            f"scaling={scaling}, direct_gain={value.direct_scoring_gain:.6f}, "
            f"contextual={value.contextual.total_gain:.3f}"
        ),
        expected="a fresh stateful scaler exposes scaling potential as contextual build evidence",
        detail=(
            "future growth is legitimate B3 evidence even before large realized Mult exists, but it remains "
            "separate from the Joker's literal present-tense scoring contribution"
        ),
    )


def _invested_scaler_has_more_realized_direct_power() -> SemanticCheck:
    evaluator = JokerBuildValueEvaluator()
    fresh = RideTheBusJoker()
    invested = RideTheBusJoker()
    invested.mult = 8
    fresh_value = evaluator.evaluate(_base_state(), fresh)
    invested_value = evaluator.evaluate(_base_state(), invested)
    fresh_scaling = STATEFUL_SCALING in set(fresh_value.contextual.descriptor.produces)
    invested_scaling = STATEFUL_SCALING in set(invested_value.contextual.descriptor.produces)
    return SemanticCheck(
        fresh_scaling
        and invested_scaling
        and float(invested_value.direct_scoring_gain) > float(fresh_value.direct_scoring_gain)
        and float(invested_value.direct_scoring_value) > float(fresh_value.direct_scoring_value),
        observed=(
            f"fresh_direct={fresh_value.direct_scoring_gain:.6f}/{fresh_value.direct_scoring_value:.3f}, "
            f"invested_direct={invested_value.direct_scoring_gain:.6f}/{invested_value.direct_scoring_value:.3f}, "
            f"fresh_scaling={fresh_scaling}, invested_scaling={invested_scaling}"
        ),
        expected="accumulated public scaler state increases literal direct-scoring value beyond a fresh copy",
        detail=(
            "B3 must distinguish scaling potential from already-realized power: the lifecycle role may be "
            "the same while accumulated public Mult materially changes present scoring strength"
        ),
    )


def _blueprint_pair_adds_contextual_copy_value() -> SemanticCheck:
    evaluator = JokerBuildValueEvaluator()
    standalone = evaluator.evaluate(_base_state(), BlueprintJoker())
    paired_state = _base_state()
    paired_state.jokers = [FlatMultJoker(4)]
    paired = evaluator.evaluate(paired_state, BlueprintJoker())
    copy_pair = any(
        interaction.kind == "COPY"
        and interaction.actor_role == "candidate"
        and interaction.target_role == "existing"
        for interaction in paired.contextual.pair_interactions
    )
    return SemanticCheck(
        copy_pair
        and float(paired.contextual.interaction_gain) > float(standalone.contextual.interaction_gain),
        observed=(
            f"copy_pair={copy_pair}, standalone_intrinsic={standalone.contextual.intrinsic_gain:.3f}, "
            f"standalone_interaction={standalone.contextual.interaction_gain:.3f}, "
            f"paired_intrinsic={paired.contextual.intrinsic_gain:.3f}, "
            f"paired_interaction={paired.contextual.interaction_gain:.3f}"
        ),
        expected="Blueprint gains additional contextual interaction value only when a concrete visible copy target exists",
        detail=(
            "copy capability may have standalone structural value, but the specific target synergy belongs in "
            "pair interaction evidence rather than being folded into the candidate's intrinsic score"
        ),
    )


def _independent_scorers_do_not_manufacture_pair_synergy() -> SemanticCheck:
    evaluator = JokerBuildValueEvaluator()
    standalone = evaluator.evaluate(_base_state(), FlatMultJoker(4))
    paired_state = _base_state()
    paired_state.jokers = [FlatMultJoker(4)]
    paired = evaluator.evaluate(paired_state, FlatMultJoker(4))
    return SemanticCheck(
        not paired.contextual.pair_interactions
        and abs(
            float(paired.contextual.interaction_gain)
            - float(standalone.contextual.interaction_gain)
        ) <= 1e-12,
        observed=(
            f"pair_interactions={len(paired.contextual.pair_interactions)}, "
            f"standalone_interaction={standalone.contextual.interaction_gain:.3f}, "
            f"paired_interaction={paired.contextual.interaction_gain:.3f}, "
            f"paired_direct={paired.direct_scoring_gain:.6f}"
        ),
        expected="independent scoring Jokers do not receive pair-only synergy from their standalone scoring output",
        detail=(
            "literal score contribution is already owned by direct scoring projection; B3 pair evidence must "
            "only credit mechanics that change because the two Jokers coexist"
        ),
    )


def _bond_adjustment_is_added_once_to_mechanical_gain() -> SemanticCheck:
    state = _base_state()
    state.money = 20
    candidate = FlatMultJoker(4)
    candidate.cost = 0
    planner = SimpleNamespace(
        evaluator=SimpleNamespace(
            evaluate=lambda projected, joker: SimpleNamespace(total_gain=3.0)
        )
    )
    policy = JokerAcquisitionPolicy(transition_planner=planner)
    original = joker_policy_module._bond_transition_bonus
    joker_policy_module._bond_transition_bonus = lambda *args, **kwargs: (2.0, ("synthetic Bond +2",))
    try:
        option = policy._score_add(state, candidate, 3.0)
    finally:
        joker_policy_module._bond_transition_bonus = original
    return SemanticCheck(
        abs(float(option.build_gain) - 5.0) <= 1e-12,
        observed=f"mechanical=3.000, bond=2.000, resulting_build_gain={option.build_gain:.3f}",
        expected="D2 adds the bounded Bond adjustment exactly once to mechanical whole-build gain",
        detail=(
            "Bond/composition evidence is a separate bounded structural term; it must not be folded into B3 "
            "literal scoring and then credited again by D2"
        ),
    )


RED_WHITE_PHASE3_BUILD_CASES = (
    SemanticBenchmarkCase(
        case_id="build.roles.scoring_engine_direct_gain",
        category="BUILD_COHERENCE",
        description="literal scoring engine exposes direct score gain",
        evaluate=_scoring_engine_exposes_direct_score_gain,
        source="Phase 3 build-evidence audit: scoring role separation",
    ),
    SemanticBenchmarkCase(
        case_id="build.roles.economy_not_direct_scoring",
        category="BUILD_COHERENCE",
        description="economy-only value remains contextual rather than fake scoring",
        evaluate=_economy_joker_does_not_manufacture_direct_score,
        source="Phase 3 build-evidence audit: economy role separation",
    ),
    SemanticBenchmarkCase(
        case_id="build.scaling.fresh_potential_is_contextual",
        category="BUILD_COHERENCE",
        description="fresh scaler exposes lifecycle potential separately from realized score",
        evaluate=_fresh_scaler_exposes_scaling_potential,
        source="Phase 3 build-evidence audit: scaling potential separation",
    ),
    SemanticBenchmarkCase(
        case_id="build.scaling.investment_increases_direct_power",
        category="BUILD_COHERENCE",
        description="public scaler investment increases literal realized scoring power",
        evaluate=_invested_scaler_has_more_realized_direct_power,
        source="Phase 3 build-evidence audit: realized scaler state",
    ),
    SemanticBenchmarkCase(
        case_id="build.interaction.blueprint_pair_only_value",
        category="BUILD_COHERENCE",
        description="Blueprint receives target-specific value through pair interaction evidence",
        evaluate=_blueprint_pair_adds_contextual_copy_value,
        source="Phase 3 build-evidence audit: pair-only contextual value",
    ),
    SemanticBenchmarkCase(
        case_id="build.interaction.independent_scoring_not_pair_synergy",
        category="BUILD_COHERENCE",
        description="standalone scoring is not duplicated as pair interaction value",
        evaluate=_independent_scorers_do_not_manufacture_pair_synergy,
        source="Phase 3 build-evidence audit: pair double-count prevention",
    ),
    SemanticBenchmarkCase(
        case_id="build.bond.adjustment_added_once",
        category="BUILD_COHERENCE",
        description="bounded Bond transition value is added exactly once after B3 mechanical value",
        evaluate=_bond_adjustment_is_added_once_to_mechanical_gain,
        source="Phase 3 build-evidence audit: Bond double-count prevention",
    ),
)
