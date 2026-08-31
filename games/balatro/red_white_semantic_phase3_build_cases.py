from __future__ import annotations

"""Phase-3 semantic cases for coherent Red/White build evidence."""

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.golden_joker import GoldenJoker
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
)
