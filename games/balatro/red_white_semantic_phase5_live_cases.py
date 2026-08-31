from __future__ import annotations

"""Phase-5 semantics derived from fresh Red/White production runs."""

from types import SimpleNamespace

import games.balatro.joker_policy as joker_policy_module
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker
from games.balatro.joker_policy import BUY, HOLD, JokerAcquisitionPolicy
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import PACE_RECOVERY, LiveHandActionPolicy
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.state import BalatroState


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


def _timeout_retained_roots_still_use_final_d1_arbiter() -> SemanticCheck:
    """Stopping search does not promote planner ordering into final action authority."""

    cards = [object() for _ in range(4)]
    play = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=cards[:2]),
        value=LiveBlindPlanValue(
            clear_probability=0.30,
            expected_progress=0.30,
            expected_score=30.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=3.0,
        ),
        horizon=2,
        exact=True,
        candidate_count=2,
    )
    discard = LiveBlindPlan(
        action=BalatroAction(DISCARD_CARDS, cards=cards[2:]),
        value=LiveBlindPlanValue(
            clear_probability=0.20,
            expected_progress=0.20,
            expected_score=20.0,
            expected_hands_remaining=4.0,
            expected_discards_remaining=2.0,
        ),
        horizon=2,
        exact=True,
        candidate_count=2,
    )

    class Evaluator:
        def project_play(self, state, action):
            del state, action
            return SimpleNamespace(expected_hand_score=10.0)

        def evaluate(self, state, action):
            del state
            return 80.0 if action.name == DISCARD_CARDS else 10.0

    engine = object.__new__(PathAwareLiveHandActionDecisionEngine)
    engine.policy = LiveHandActionPolicy(evaluator=Evaluator())
    engine._adaptive_plan_history = [(play, discard)]
    engine._adaptive_root_history = []
    state = SimpleNamespace(
        hand=cards,
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=4,
        discards_remaining=3,
    )

    decision = engine._structural_timeout_fallback(state, search_attempts=())
    passed = decision.mode == PACE_RECOVERY and decision.action is discard.action
    return SemanticCheck(
        passed,
        observed=f"mode={decision.mode}, action={decision.action.name}",
        expected=(
            "timeout reuses the latest completed plan set through the canonical D1 "
            "Play-vs-Discard arbiter"
        ),
        detail=(
            "a wall-clock deadline may stop additional search, but planner root ordering "
            "cannot become a second final controller; complete public hand state must still "
            "flow through LiveHandActionPolicy before execution"
        ),
    )


class _SupportOnlyJoker(Joker):
    """Synthetic positive-build Joker with no direct scoring effect."""

    def apply(self, context):
        return context


class _FirstEngineTransitionPlanner:
    def __init__(self, *, direct_scoring_gain: float) -> None:
        self.direct_scoring_gain = float(direct_scoring_gain)

    def plan(self, state, candidate):
        del state, candidate
        return SimpleNamespace(
            candidate_value=SimpleNamespace(
                applicability="APPLICABLE",
                total_gain=0.50,
                direct_scoring_gain=self.direct_scoring_gain,
            ),
            alternatives=(),
        )


def _first_joker_bootstrap_requires_current_scoring_power() -> SemanticCheck:
    """Structural/economy value alone is not the early scoring-foothold exception."""

    def state() -> BalatroState:
        current = BalatroState()
        current.phase = "SHOP"
        current.ante = 1
        current.money = 6
        current.joker_slots = 5
        current.jokers = []
        return current

    support = _SupportOnlyJoker()
    support.cost = 4
    scoring = FlatMultJoker(4)
    scoring.cost = 4

    original = joker_policy_module._bond_transition_bonus
    joker_policy_module._bond_transition_bonus = lambda state, candidate, **kwargs: (0.0, ())
    try:
        support_decision = JokerAcquisitionPolicy(
            transition_planner=_FirstEngineTransitionPlanner(direct_scoring_gain=0.0)
        ).decide(state(), support)
        scoring_decision = JokerAcquisitionPolicy(
            transition_planner=_FirstEngineTransitionPlanner(direct_scoring_gain=0.25)
        ).decide(state(), scoring)
    finally:
        joker_policy_module._bond_transition_bonus = original

    passed = support_decision.action == HOLD and scoring_decision.action == BUY
    return SemanticCheck(
        passed,
        observed=(
            f"support={support_decision.action}, scoring={scoring_decision.action}"
        ),
        expected=(
            "the Ante-1/2 first-Joker reserve relaxation stays HOLD for positive structural "
            "value without current scoring power, while a true scoring foothold may use it"
        ),
        detail=(
            "Phase-5 live attempt 1 exhausted all four discards and still died 544/800 with "
            "Midas Mask as its only Joker. D2 may value support/deck-development normally, but "
            "that value cannot inherit the special first-scoring-engine authority unless the "
            "canonical literal whole-build projection finds positive direct scoring gain"
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
    SemanticBenchmarkCase(
        case_id="d1.live.timeout_preserves_final_arbiter",
        category="D1_SURVIVAL",
        description="D1 timeout keeps final Play-vs-Discard arbitration authoritative",
        evaluate=_timeout_retained_roots_still_use_final_d1_arbiter,
        source=(
            "Phase 5 post-fix live baseline: two losses still ended with every discard unused, "
            "including an Ante-1 Big Blind at 74/450"
        ),
    ),
    SemanticBenchmarkCase(
        case_id="d2.live.first_joker_bootstrap_requires_scoring_foothold",
        category="SHOP_SURVIVAL",
        description="early first-Joker bootstrap requires current literal scoring power",
        evaluate=_first_joker_bootstrap_requires_current_scoring_power,
        source=(
            "Phase 5 72/72 live baseline: attempt 1 spent all four discards but died Ante 2 "
            "at 544/800 with Midas Mask as its only Joker"
        ),
    ),
)
