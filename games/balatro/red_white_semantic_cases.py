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
    LiveBlindPlan,
    LiveBlindPlanValue,
)
from games.balatro.live.hand_action_policy import PACE_PLAY, PACE_RECOVERY, LiveHandActionPolicy
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.mouth_hand_policy import apply_mouth_first_hand_policy
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


def _timeout_reuses_completed_d1_evidence() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    canonical_discard = LiveBlindPlan(
        action=BalatroAction(DISCARD_CARDS, cards=cards[:3]),
        value=LiveBlindPlanValue(
            clear_probability=0.40,
            expected_progress=0.65,
            expected_score=65.0,
            expected_hands_remaining=4.0,
            expected_discards_remaining=3.0,
        ),
        horizon=3,
        exact=True,
        candidate_count=2,
    )
    weaker_play = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=cards[:1]),
        value=LiveBlindPlanValue(
            clear_probability=0.05,
            expected_progress=0.15,
            expected_score=15.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
        ),
        horizon=3,
        exact=True,
        candidate_count=2,
    )
    engine = object.__new__(PathAwareLiveHandActionDecisionEngine)
    engine.policy = LiveHandActionPolicy()
    engine._adaptive_plan_history = [(canonical_discard, weaker_play)]
    engine._adaptive_root_history = []
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=4,
        discards_remaining=4,
    )

    decision = engine._structural_timeout_fallback(state, search_attempts=())
    retained = decision.action is canonical_discard.action
    structural = any("structural" in note.lower() for note in decision.rationale)
    return SemanticCheck(
        retained and not structural,
        observed=(
            f"selected={decision.action.name}, retained={retained}, "
            f"rationale={decision.rationale!r}"
        ),
        expected="timeout returns the best completed canonical D1 root",
        detail="wall-clock exhaustion may stop more search but must not replace completed survival evidence with the poker-hand/rank structural heuristic",
    )


def _finalized_d1_action_class_is_authoritative() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    pace_play = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=cards[:2]),
        value=LiveBlindPlanValue(
            clear_probability=0.20,
            expected_progress=0.40,
            expected_score=40.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )
    deeper_discard = LiveBlindPlan(
        action=BalatroAction(DISCARD_CARDS, cards=cards[2:]),
        value=LiveBlindPlanValue(
            clear_probability=0.60,
            expected_progress=0.80,
            expected_score=80.0,
            expected_hands_remaining=4.0,
            expected_discards_remaining=3.0,
        ),
        horizon=3,
        exact=True,
        candidate_count=2,
    )
    state = SimpleNamespace(hand=cards)
    policy = LiveHandActionPolicy()
    decision = policy._decision(
        mode=PACE_PLAY,
        selected=pace_play,
        best_play=pace_play,
        best_discard=deeper_discard,
        pace_target=25.0,
        best_play_immediate_score=40.0,
        best_play_pace_ratio=1.6,
        selected_immediate_score=40.0,
        selected_pace_ratio=1.6,
        selected_fallback_value=None,
        clear_path_candidates=0,
        sampled_clear_path_confirmed=False,
        setup_discard_consensus=False,
        confidence=0.80,
        rationale=("production policy selected a pace-qualified Play",),
        plans=(pace_play, deeper_discard),
        search_attempts=(),
    )
    engine = object.__new__(PathAwareLiveHandActionDecisionEngine)
    engine.policy = policy
    engine._adaptive_root_history = [(None, deeper_discard)]

    resolved = engine._apply_adaptive_authority(state, decision)
    retained_class = resolved.action.name == PLAY_CARDS
    return SemanticCheck(
        retained_class and resolved.action is pace_play.action,
        observed=f"selected={resolved.action.name}, expected={PLAY_CARDS}",
        expected="post-policy adaptive evidence cannot flip the finalized Play/Discard class",
        detail="deeper search may refine a candidate within the survival action class, but a post-return wrapper is not a second Play-vs-Discard controller",
    )


def _canonical_safe_pace_owns_action_class() -> SemanticCheck:
    """The production strategy policy itself, not an installer, owns safe pace."""
    cards = [object() for _ in range(4)]
    pace_play = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=cards[:2]),
        value=LiveBlindPlanValue(
            clear_probability=0.20,
            expected_progress=0.40,
            expected_score=40.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )
    deeper_discard = LiveBlindPlan(
        action=BalatroAction(DISCARD_CARDS, cards=cards[2:]),
        value=LiveBlindPlanValue(
            clear_probability=0.80,
            expected_progress=0.90,
            expected_score=90.0,
            expected_hands_remaining=4.0,
            expected_discards_remaining=3.0,
        ),
        horizon=3,
        exact=True,
        candidate_count=2,
    )
    baseline_policy = LiveHandActionPolicy()
    baseline = baseline_policy._decision(
        mode="CLEAR_PATH",
        selected=deeper_discard,
        best_play=pace_play,
        best_discard=deeper_discard,
        pace_target=25.0,
        best_play_immediate_score=30.0,
        best_play_pace_ratio=1.2,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=None,
        clear_path_candidates=1,
        sampled_clear_path_confirmed=False,
        setup_discard_consensus=False,
        confidence=0.80,
        rationale=("deeper search preferred discard",),
        plans=(pace_play, deeper_discard),
        search_attempts=(),
    )

    class Evaluator:
        def project_play(self, state, action):
            return SimpleNamespace(
                expected_hand_score=30.0,
                clear_probability=0.20,
                outcomes=(),
            )

        def evaluate(self, state, action):
            return 100.0 if action.name == DISCARD_CARDS else 30.0

    policy = object.__new__(StrategyAwareLiveHandActionPolicy)
    policy.evaluator = Evaluator()
    policy.thresholds = SimpleNamespace(pace_ratio_floor=1.0)
    policy.build_evaluator = SimpleNamespace(
        prepare=lambda state: None,
        reset_cache=lambda: None,
    )
    policy._ranking_state = None
    policy._pace_target = lambda state: 25.0
    policy._pace_ratio = lambda score, target: score / target
    policy._within_type_key = lambda plan: (
        plan.value.clear_probability,
        plan.value.expected_progress,
        plan.value.expected_hands_remaining,
        plan.value.expected_discards_remaining,
        plan.value.expected_score,
    )
    policy._safe_equivalent_clear_key = lambda plan: (
        plan.value.expected_hands_remaining,
        plan.value.expected_discards_remaining,
        plan.value.clear_probability,
    )
    policy._pace_play_key = lambda plan, ratio: (
        plan.value.clear_probability,
        plan.value.expected_progress,
        ratio,
    )
    policy._pace_confidence = lambda ratio: min(1.0, ratio)

    state = SimpleNamespace(hands_remaining=4, discards_remaining=4)
    decision = policy._enforce_safe_pace_scope(
        state,
        (pace_play, deeper_discard),
        baseline,
        setup_discard_consensus=False,
    )
    return SemanticCheck(
        decision.mode == PACE_PLAY and decision.action is pace_play.action,
        observed=f"mode={decision.mode}, action={decision.action.name}",
        expected="canonical StrategyAware D1 chooses pace-qualified PLAY without a scope wrapper",
        detail="multi-step clear evidence may rank within the action class but may not replace an available Red/White pace play",
    )


def _mouth_refinement_preserves_action_class() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    play = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=cards[:2]),
        value=LiveBlindPlanValue(0.95, 0.8, 80.0, 3.0, 3.0),
        horizon=1,
        exact=True,
        candidate_count=2,
    )
    discard = LiveBlindPlan(
        action=BalatroAction(DISCARD_CARDS, cards=cards[2:]),
        value=LiveBlindPlanValue(0.40, 0.5, 50.0, 4.0, 2.0),
        horizon=2,
        exact=True,
        candidate_count=2,
    )
    base_policy = LiveHandActionPolicy()
    decision = base_policy._decision(
        mode=PACE_RECOVERY,
        selected=discard,
        best_play=play,
        best_discard=discard,
        pace_target=25.0,
        best_play_immediate_score=80.0,
        best_play_pace_ratio=3.2,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=25.0,
        clear_path_candidates=0,
        sampled_clear_path_confirmed=False,
        setup_discard_consensus=False,
        confidence=0.5,
        rationale=("canonical D1 selected DISCARD",),
        plans=(play, discard),
        search_attempts=(),
    )
    policy = SimpleNamespace(
        EPSILON=1e-9,
        _hand_bond_intents=lambda state: (),
        _strategy_fit=lambda state, action: (0.0, ()),
        _within_type_key=lambda plan: (plan.value.clear_probability,),
        evaluator=SimpleNamespace(
            evaluate=lambda state, action: 10.0,
            project_play=lambda state, action: SimpleNamespace(expected_hand_score=999.0),
        ),
    )
    state = SimpleNamespace(
        boss_name="The Mouth",
        boss_blind_only_hand=None,
        round_hand_play_counts={},
        jokers=(),
        discards_remaining=2,
    )
    resolved = apply_mouth_first_hand_policy(policy, state, (play, discard), decision)
    return SemanticCheck(
        resolved.action.name == DISCARD_CARDS,
        observed=f"canonical={decision.action.name}, resolved={resolved.action.name}",
        expected="Mouth first-hand refinement preserves canonical DISCARD action class",
        detail="boss strategy shaping may refine the selected class but cannot become a second Play-vs-Discard arbiter",
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
        "d1.authority.timeout_consistency",
        "D1_SURVIVAL",
        "A timeout after completed adaptive search must retain canonical D1 evidence.",
        _timeout_reuses_completed_d1_evidence,
        source="Phase-2 authority audit: timeout/fallback objective divergence",
    ),
    SemanticBenchmarkCase(
        "d1.authority.action_class",
        "D1_SURVIVAL",
        "Post-policy adaptive evidence cannot reverse the finalized Play/Discard class.",
        _finalized_d1_action_class_is_authoritative,
        source="Phase-0 authority audit: PathAware post-policy arbitration",
    ),
    SemanticBenchmarkCase(
        "d1.authority.canonical_safe_pace",
        "D1_SURVIVAL",
        "The production strategy-aware D1 policy itself must own safe-pace action arbitration.",
        _canonical_safe_pace_owns_action_class,
        source="Phase-0 consolidation: retired safe_pace_scope_correction wrapper",
    ),
    SemanticBenchmarkCase(
        "d1.authority.mouth_action_class",
        "D1_SURVIVAL",
        "The Mouth first-hand strategy refinement cannot reverse canonical Play/Discard authority.",
        _mouth_refinement_preserves_action_class,
        source="Phase-0 consolidation: Mouth first-hand wrapper action-class boundary",
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
