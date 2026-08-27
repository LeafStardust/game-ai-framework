from __future__ import annotations

from types import SimpleNamespace

import games.balatro.build.joker_strategy as joker_strategy
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.hand import PokerHand
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


def _repeated_hand_projection_is_native_b3() -> SemanticCheck:
    evaluator = object.__new__(JokerBuildValueEvaluator)
    evaluator._scoring_probes = lambda state: ((PokerHand.PAIR, ()),)
    evaluator._direct_scoring_gain_for_state = lambda state, joker: (
        10.0
        if int((getattr(state, "round_hand_play_counts", {}) or {}).get("PAIR", 0) or 0) > 0
        else 0.0
    )

    original_analyzer = joker_strategy._SCENARIO_ANALYZER
    joker_strategy._SCENARIO_ANALYZER = SimpleNamespace(
        describe=lambda joker: SimpleNamespace(
            requires=frozenset({joker_strategy._REPEATED_HAND_SCENARIO})
        )
    )
    try:
        gain = evaluator._direct_scoring_gain(
            SimpleNamespace(round_hand_play_counts={}),
            FlatMultJoker(4),
        )
    finally:
        joker_strategy._SCENARIO_ANALYZER = original_analyzer

    return SemanticCheck(
        abs(float(gain) - 5.0) <= 1e-12,
        observed=f"native repeated-hand direct gain={float(gain):.3f}",
        expected="5.000 average of inactive 0 and reachable-active 10",
        detail=(
            "B3 itself must expose reachable repeated-hand conditional scoring; "
            "no late Red/White direct-scoring monkeypatch remains"
        ),
    )


RED_WHITE_NATIVE_BUILD_CASES = (
    SemanticBenchmarkCase(
        case_id="b3.authority.repeated_hand_projection",
        category="BUILD_COHERENCE",
        description="native B3 includes reachable repeated-hand scoring context",
        evaluate=_repeated_hand_projection_is_native_b3,
    ),
)
