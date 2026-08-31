from __future__ import annotations

"""Phase-3 semantic cases for coherent Red/White build evidence."""

from games.balatro.build.joker_lifecycle import STATEFUL_SCALING
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
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
)
