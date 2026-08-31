from __future__ import annotations

"""Phase-5 semantics for final-hand discard recovery discovered in live play."""

from games.balatro.safe_pace_optimization_policy import _safe_search_schedule
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


def _final_hand_schedule_can_spend_all_remaining_discards() -> SemanticCheck:
    """One scoring hand may be preceded by every remaining discard.

    Phase-5 live validation reached The Needle with one scoring hand and four
    discards, then lost 550/800 after spending none of those discards.  The
    production safe schedule exposed only horizon two, so D1 could represent at
    most one discard followed by the final play.  This is a search-scope mechanic:
    discards do not consume the remaining scoring hand, so the bounded planner must
    be able to compare the complete legal discard chain before that final Play.

    Ordinary multi-hand states remain deliberately shallow.
    """
    final_hand = _safe_search_schedule(
        hands_remaining=1,
        discards_remaining=4,
        max_horizon=8,
        max_nodes=5000,
    )
    ordinary = _safe_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=8,
        max_nodes=5000,
    )

    final_horizon = final_hand[0].horizon if final_hand else 0
    ordinary_horizon = ordinary[0].horizon if ordinary else 0
    passed = final_horizon == 5 and ordinary_horizon == 2
    return SemanticCheck(
        passed,
        observed=(
            f"one_hand_four_discards_horizon={final_horizon}, "
            f"ordinary_four_hand_horizon={ordinary_horizon}"
        ),
        expected=(
            "one remaining scoring hand with four discards exposes the bounded "
            "five-action discard-chain horizon while ordinary multi-hand D1 stays shallow"
        ),
        detail=(
            "discard actions do not consume the last scoring hand; a horizon-two-only "
            "schedule can therefore hide legal survival lines that use multiple discards "
            "before the final Play"
        ),
    )


RED_WHITE_PHASE5_FINAL_HAND_CASES = (
    SemanticBenchmarkCase(
        case_id="d1.live.final_hand_search_spends_remaining_discards",
        category="D1_SURVIVAL",
        description="final-hand D1 can search the full bounded discard chain before Play",
        evaluate=_final_hand_schedule_can_spend_all_remaining_discards,
        source=(
            "Phase 5 73/73 live baseline: The Needle loss at 550/800 ended with the "
            "sole scoring hand spent and all 4/4 discards unused"
        ),
    ),
)
