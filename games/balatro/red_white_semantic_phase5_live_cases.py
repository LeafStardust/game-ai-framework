from __future__ import annotations

"""Phase-5 semantics derived from fresh Red/White production runs."""

from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


def _underpace_made_hand_does_not_suppress_discard_recovery() -> SemanticCheck:
    """Hand class cannot override the actual pace deficit during D1 recovery.

    The Phase-5 baseline lost three independent runs with all four discards still
    unused.  The canonical evaluator had been applying a categorical -250 discard
    penalty whenever the current best visible play happened to classify as a
    Straight/Flush/Full House/Four of a Kind/Straight Flush, even when that play was
    materially below the chips-per-hand pace required to survive.

    Hold every literal recovery input constant and vary only that poker-hand label.
    While both visible plays are below pace, discard value must be identical: the
    opportunity cost is already represented by the actual projected score/pace.
    """

    cards = [
        BalatroCard("A", "Spades", live_id="a"),
        BalatroCard("A", "Hearts", live_id="ah"),
        BalatroCard("7", "Clubs", live_id="7"),
        BalatroCard("5", "Diamonds", live_id="5"),
        BalatroCard("2", "Clubs", live_id="2"),
    ]
    action = BalatroAction(DISCARD_CARDS, cards=cards[2:])
    state = SimpleNamespace(
        hand=cards,
        discards_remaining=4,
        hands_remaining=4,
    )

    evaluator = LiveHandDecisionEvaluator()
    evaluator._has_guaranteed_clearing_play = lambda current: False

    common = dict(
        remaining_chips=400.0,
        required_per_hand=100.0,
        best_play_score=25.0,
    )
    made_context = SimpleNamespace(**common, best_play_hand=PokerHand.FLUSH)
    ordinary_context = SimpleNamespace(**common, best_play_hand=PokerHand.TWO_PAIR)

    made_value = evaluator._discard_value(state, action, made_context)
    ordinary_value = evaluator._discard_value(state, action, ordinary_context)
    same_value = abs(made_value - ordinary_value) <= 1e-12

    return SemanticCheck(
        same_value,
        observed=(
            f"underpace_flush_discard={made_value:.3f}, "
            f"underpace_two_pair_discard={ordinary_value:.3f}"
        ),
        expected=(
            "equally under-pace visible plays give the same discard-recovery value "
            "regardless of made-hand class"
        ),
        detail=(
            "D1 may protect a made hand when it satisfies current survival pace, but "
            "poker-hand class alone cannot make an under-pace discard unavailable; "
            "doing so burns scoring hands while leaving the run's discard resource unused"
        ),
    )


RED_WHITE_PHASE5_LIVE_CASES = (
    SemanticBenchmarkCase(
        case_id="d1.live.underpace_made_hand_keeps_discard_recovery",
        category="D1_SURVIVAL",
        description="under-pace made hands do not categorically suppress discard recovery",
        evaluate=_underpace_made_hand_does_not_suppress_discard_recovery,
        source="Phase 5 three-run live baseline: all losses ended with 4/4 discards unused",
    ),
)
