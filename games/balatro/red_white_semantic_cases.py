from __future__ import annotations

"""Initial Red/White semantic competence cases.

These are intentionally reconstructed public-state properties derived from live
failure classes. They are not tuned to exact card indices unless the mechanic
itself demands exactness.
"""

from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.joker_policy import BUY, HOLD, JokerAcquisitionPolicy
from games.balatro.jokers.card_sharp import CardSharpJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    LiveBlindPlanValue,
    _ActionEstimate,
)
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy
from games.balatro.state import BalatroState


def _underpace_multi_discard() -> SemanticCheck:
    evaluator = object.__new__(LiveHandDecisionEvaluator)
    evaluator._cached_state_id = None
    evaluator._cached_context = None
    evaluator.scorer = SimpleNamespace(is_card_debuffed=lambda card: False)
    evaluator._has_guaranteed_clearing_play = lambda state: False
    evaluator._retained_structure_value = lambda cards: 0.0

    cards = [object() for _ in range(8)]
    state = SimpleNamespace(hand=cards, discards_remaining=4, hands_remaining=4)
    context = SimpleNamespace(
        best_play_score=25.0,
        required_per_hand=100.0,
        best_play_hand=None,
    )
    single = BalatroAction(DISCARD_CARDS, cards=cards[:1])
    batch = BalatroAction(DISCARD_CARDS, cards=cards[:4])
    single_value = evaluator._discard_value(state, single, context)
    batch_value = evaluator._discard_value(state, batch, context)
    passed = batch_value > single_value
    return SemanticCheck(
        passed,
        observed=f"single={single_value:.3f}, multi={batch_value:.3f}",
        expected="multi-card recovery discard outranks single-card discard",
        detail="both consume one discard resource while the build is badly under pace",
    )


def _planner_discard_beam_uses_d1_value() -> SemanticCheck:
    class RecordingEvaluator:
        def __init__(self):
            self.calls = []

        def evaluate(self, state, action):
            self.calls.append((state, action))
            return 100.0 * len(action.cards)

    evaluator = RecordingEvaluator()
    planner = object.__new__(LiveBlindClearPlanner)
    planner.evaluator = evaluator
    cards = [object() for _ in range(4)]
    state = SimpleNamespace(hand=cards)
    single = BalatroAction(DISCARD_CARDS, cards=cards[:1])
    batch = BalatroAction(DISCARD_CARDS, cards=cards[:4])
    single_priority = planner._discard_priority(state, single)
    batch_priority = planner._discard_priority(state, batch)
    passed = batch_priority > single_priority and len(evaluator.calls) == 2
    return SemanticCheck(
        passed,
        observed=f"single={single_priority!r}, multi={batch_priority!r}",
        expected="planner discard beam preserves canonical D1 ordering",
        detail="candidate pre-ranking must not silently use a separate recovery objective",
    )


def _planner_progress_beats_exactness_without_clear() -> SemanticCheck:
    low_progress_exact = _ActionEstimate(
        BalatroAction(PLAY_CARDS),
        LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.20,
            expected_score=200.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
        ),
        True,
    )
    high_progress_sampled = _ActionEstimate(
        BalatroAction(PLAY_CARDS),
        LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.80,
            expected_score=800.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
        ),
        False,
    )
    exact_key = LiveBlindClearPlanner._estimate_key(low_progress_exact)
    sampled_key = LiveBlindClearPlanner._estimate_key(high_progress_sampled)
    return SemanticCheck(
        sampled_key > exact_key,
        observed=f"exact={exact_key!r}, higher_progress_sampled={sampled_key!r}",
        expected="when clear probability is equal, progress outranks evidence exactness",
        detail="exactness is confidence metadata; it must not make a much worse non-clear line strategically preferable",
    )


def _first_scoring_foothold() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 1
    state.money = 7
    state.joker_slots = 5
    state.jokers = []
    candidate = FlatMultJoker(4)
    candidate.cost = 4
    candidate.discovered = True
    decision = JokerAcquisitionPolicy().decide(state, candidate)
    return SemanticCheck(
        decision.action == BUY,
        observed=str(decision.action),
        expected="BUY",
        detail="an affordable mechanically positive first scoring foothold must not lose solely to reserve preference",
    )


def _strategy_conflict_veto() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.money = 30
    state.ante = 3
    state.joker_slots = 5
    state.jokers = [ScaryFaceJoker()]
    decision = PlaybookJokerAcquisitionPolicy(JokerBuildTransitionPlanner()).decide(
        state, RideTheBusJoker()
    )
    conflict = any("canonical Bond conflict veto" in note for note in decision.rationale)
    return SemanticCheck(
        decision.action == HOLD and conflict,
        observed=f"action={decision.action}, conflict_veto={conflict}",
        expected="HOLD with canonical semantic conflict veto",
        detail="generic early-scoring or Build Health rescue may not override a real face-card/no-face-card conflict",
    )


def _first_engine_before_hand_size_voucher() -> SemanticCheck:
    state = SimpleNamespace(ante=1, jokers=[], hand_levels={"PAIR": 1})
    profile = SimpleNamespace(ante=1, joker_names=(), hand_levels=(("PAIR", 1),))
    allowed, notes = VoucherAcquisitionPolicy._early_survival_gate(
        state,
        profile,
        "Paint Brush",
        price=10,
        money_after=4,
    )
    explicit = any("first-engine hold" in note for note in notes)
    return SemanticCheck(
        not allowed and explicit,
        observed=f"allowed={allowed}, explicit_first_engine_hold={explicit}",
        expected="expensive hand-size voucher held until first scoring foothold",
        detail="support utility cannot pre-empt basic Ante-1 survival with zero Jokers and no invested hand",
    )


def _reachable_conditional_scoring_is_visible() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.jokers = []
    state.round_hand_play_counts = {
        hand: 0 for hand in state.round_hand_play_counts
    }
    value = JokerBuildValueEvaluator().evaluate(state, CardSharpJoker())
    return SemanticCheck(
        value.direct_scoring_gain > 0.0 and value.direct_scoring_value > 0.0,
        observed=(
            f"direct_scoring_gain={value.direct_scoring_gain:.3f}, "
            f"direct_scoring_value={value.direct_scoring_value:.3f}"
        ),
        expected="reachable repeated-hand scoring contributes positive contextual value",
        detail="conditional mechanics should be modeled through reachable literal contexts, not ignored because a neutral probe is inactive",
    )


RED_WHITE_SEMANTIC_CASES = (
    SemanticBenchmarkCase(
        "d1.recovery.multi_redraw",
        "D1_SURVIVAL",
        "Under pace, a useful multi-card redraw should outrank a wasteful one-card discard.",
        _underpace_multi_discard,
        source="live failure class: repeated one-card recovery discards",
    ),
    SemanticBenchmarkCase(
        "d1.authority.candidate_beam",
        "D1_SURVIVAL",
        "Discard candidate ranking must use the canonical D1 evaluator.",
        _planner_discard_beam_uses_d1_value,
        source="live failure class: planner/controller objective disagreement",
    ),
    SemanticBenchmarkCase(
        "d1.authority.progress_before_exactness",
        "D1_SURVIVAL",
        "Evidence exactness cannot outrank materially better progress when clear probability is equal.",
        _planner_progress_beats_exactness_without_clear,
        source="Phase-2 authority audit: planner estimate ordering",
    ),
    SemanticBenchmarkCase(
        "shop.survival.first_scoring_foothold",
        "SHOP_SURVIVAL",
        "A legal affordable first scoring engine should be admitted in early survival.",
        _first_scoring_foothold,
        source="live failure class: empty early scoring board rejected useful Joker",
    ),
    SemanticBenchmarkCase(
        "shop.conflict.face_vs_no_face",
        "SHOP_SURVIVAL",
        "A real strategy/mechanical conflict remains authoritative over generic rescue logic.",
        _strategy_conflict_veto,
        source="deterministic regression exposed by early-scoring rescue",
    ),
    SemanticBenchmarkCase(
        "shop.survival.first_engine_before_hand_size",
        "SHOP_SURVIVAL",
        "Expensive hand-size utility cannot pre-empt the first scoring foothold.",
        _first_engine_before_hand_size_voucher,
        source="Red/White early survival authority",
    ),
    SemanticBenchmarkCase(
        "build.context.card_sharp_repeated_hand",
        "BUILD_COHERENCE",
        "Reachable conditional scoring must appear in literal contextual Joker value.",
        _reachable_conditional_scoring_is_visible,
        source="live failure class: neutral probes omitted reachable scoring context",
    ),
)