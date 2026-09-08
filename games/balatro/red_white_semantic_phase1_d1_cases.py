from __future__ import annotations

"""Phase-1 semantic cases for Red/White D1 survival competence."""

from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, USE_CONSUMABLE, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as CoreD1LiveBlindClearPlanner,
)
from games.balatro.live.hand_action_policy import PACE_RECOVERY, LiveHandActionPolicy
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


class _DiscardRecordingActions:
    def __init__(self, play_action: BalatroAction, discard_action: BalatroAction) -> None:
        self.play_action = play_action
        self.discard_action = discard_action
        self.discard_calls = 0

    def generate_discard_actions(self, state):
        del state
        self.discard_calls += 1
        return [self.discard_action]


class _GuaranteedClearPlanner(CoreD1LiveBlindClearPlanner):
    """Minimal harness around the canonical D1 candidate-spend decision."""

    def __init__(self, actions: _DiscardRecordingActions) -> None:
        self.action_generator = actions
        self.play_width = 4
        self.discard_width = 4
        self.nodes_evaluated = 0
        self._play_projection_cache = {}
        self._consumable_estimate_cache = {}

    def _root_play_candidates(self, state, play_limit: int):
        del state, play_limit
        return [self.action_generator.play_action]

    def _play_projection(self, state, action):
        del state, action
        return SimpleNamespace(clears_blind=True)

    def _play_priority(self, state, action):
        del state, action
        return (1.0, 100.0, 100.0, -1, 0)


def _plan(
    action: BalatroAction,
    *,
    clear_probability: float = 0.10,
    exact: bool = True,
) -> LiveBlindPlan:
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear_probability,
            expected_progress=0.20,
            expected_score=20.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=2.0,
        ),
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


def _guaranteed_clear_does_not_spend_discard() -> SemanticCheck:
    card = SimpleNamespace(rank="A", suit="Spades")
    play = BalatroAction(PLAY_CARDS, cards=[card])
    discard = BalatroAction(DISCARD_CARDS, cards=[card])
    actions = _DiscardRecordingActions(play, discard)
    planner = _GuaranteedClearPlanner(actions)
    state = SimpleNamespace(discards_remaining=3)

    candidates = planner._candidate_actions(state, allow_discards=True)
    passed = candidates == [play] and actions.discard_calls == 0
    return SemanticCheck(
        passed,
        observed=(
            f"candidate_names={[action.name for action in candidates]!r}, "
            f"discard_generation_calls={actions.discard_calls}"
        ),
        expected="a guaranteed visible clear suppresses discard generation entirely",
        detail=(
            "D1 must not spend a discard resource searching for development or score once a "
            "currently visible legal Play already guarantees survival"
        ),
    )


def _recursive_cerulean_candidates_preserve_forced_legality() -> SemanticCheck:
    forced = BalatroCard("A", "Spades", live_id="forced")
    forced.forced_selection = True
    others = [
        BalatroCard("K", "Hearts", live_id="k"),
        BalatroCard("Q", "Clubs", live_id="q"),
        BalatroCard("J", "Diamonds", live_id="j"),
        BalatroCard("10", "Hearts", live_id="10"),
    ]
    state = SimpleNamespace(
        hand=[forced, *others],
        boss_name="Cerulean Bell",
        jokers=(),
    )

    planner = D1LiveBlindClearPlanner(horizon=2)
    candidates = planner._child_play_candidates(state, play_limit=6)
    all_legal = bool(candidates) and all(
        boss_play_action_is_legal(state, action) for action in candidates
    )
    all_include_forced = bool(candidates) and all(
        forced in tuple(action.cards or ()) for action in candidates
    )
    return SemanticCheck(
        all_legal and all_include_forced,
        observed=(
            f"count={len(candidates)}, all_legal={all_legal}, "
            f"all_include_forced={all_include_forced}"
        ),
        expected="recursive Cerulean Play candidates obey the same forced-card legality as the root",
        detail=(
            "bounded recursive search must not manufacture hypothetical actions that would be "
            "illegal at the authoritative checkpoint"
        ),
    )


def _underpace_play_yields_to_material_redraw() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    play = _plan(BalatroAction(PLAY_CARDS, cards=cards[:2]))
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=cards[2:]))

    class Evaluator:
        def project_play(self, state, action):
            del state, action
            return SimpleNamespace(expected_hand_score=10.0)

        def evaluate(self, state, action):
            del state
            return 50.0 if action.name == DISCARD_CARDS else 10.0

    policy = LiveHandActionPolicy(evaluator=Evaluator())
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=4,
        discards_remaining=3,
    )
    decision = policy.decide(state, (play, discard))
    passed = decision.mode == PACE_RECOVERY and decision.action is discard.action
    return SemanticCheck(
        passed,
        observed=f"mode={decision.mode}, action={decision.action.name}",
        expected="under-pace D1 recovery selects the materially stronger discard redraw",
        detail=(
            "when no current Play reaches required pace, immediate chip gain must not crowd out "
            "a substantially better canonical recovery redraw"
        ),
    )


def _last_discard_is_not_spent_for_marginal_recovery() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    play = _plan(BalatroAction(PLAY_CARDS, cards=cards[:2]))
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=cards[2:]))

    class Evaluator:
        def project_play(self, state, action):
            del state, action
            return SimpleNamespace(expected_hand_score=10.0)

        def evaluate(self, state, action):
            del state
            return 15.0 if action.name == DISCARD_CARDS else 10.0

    policy = LiveHandActionPolicy(evaluator=Evaluator())
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=4,
        discards_remaining=1,
    )
    decision = policy.decide(state, (play, discard))
    passed = decision.mode == PACE_RECOVERY and decision.action is play.action
    return SemanticCheck(
        passed,
        observed=f"mode={decision.mode}, action={decision.action.name}",
        expected="the final discard is conserved when its recovery edge is only marginal",
        detail=(
            "D1's low-discard reserve is part of the canonical recovery objective: a small redraw "
            "advantage must not consume the last recovery resource"
        ),
    )


def _timeout_reuses_latest_completed_root() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    earlier_discard = _plan(BalatroAction(DISCARD_CARDS, cards=cards[:2]))
    latest_play = _plan(BalatroAction(PLAY_CARDS, cards=cards[2:]), clear_probability=0.30)
    latest_discard = _plan(BalatroAction(DISCARD_CARDS, cards=cards[:3]), clear_probability=0.20)

    engine = object.__new__(PathAwareLiveHandActionDecisionEngine)
    engine.policy = LiveHandActionPolicy()
    engine._adaptive_plan_history = [
        (earlier_discard, latest_play),
        (latest_play, latest_discard),
    ]
    engine._adaptive_root_history = []
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=4,
        discards_remaining=3,
    )

    decision = engine._structural_timeout_fallback(state, search_attempts=())
    used_latest = decision.action is latest_play.action
    avoided_structural = not any("structural" in note.lower() for note in decision.rationale)
    return SemanticCheck(
        used_latest and avoided_structural,
        observed=(
            f"selected={decision.action.name}, used_latest={used_latest}, "
            f"avoided_structural={avoided_structural}"
        ),
        expected="timeout reuses the latest fully completed canonical root ranking",
        detail=(
            "a later adaptive pass that times out may stop more search, but it may not rewind to "
            "older evidence or replace completed D1 evidence with the emergency structural heuristic"
        ),
    )


def _timeout_does_not_promote_unconfirmed_sampled_clear() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    sampled_play = _plan(
        BalatroAction(PLAY_CARDS, cards=cards[:2]),
        clear_probability=0.90,
        exact=False,
    )
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=cards[2:]), clear_probability=0.25)

    engine = object.__new__(PathAwareLiveHandActionDecisionEngine)
    engine.policy = LiveHandActionPolicy()
    engine._adaptive_plan_history = [(sampled_play, discard)]
    engine._adaptive_root_history = []
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=4,
        discards_remaining=3,
    )

    decision = engine._structural_timeout_fallback(state, search_attempts=())
    return SemanticCheck(
        decision.mode == PACE_RECOVERY
        and decision.action is sampled_play.action
        and decision.sampled_clear_path_confirmed is False,
        observed=(
            f"mode={decision.mode}, action={decision.action.name}, "
            f"sampled_confirmed={decision.sampled_clear_path_confirmed}"
        ),
        expected="timeout retains sampled evidence without promoting it to a confirmed clear path",
        detail=(
            "wall-clock exhaustion cannot manufacture confirmation: an inexact sampled line above "
            "the clear floor remains recovery evidence until an independent confirmation pass completes"
        ),
    )


def _last_hand_prefers_useful_discard_over_underpace_play() -> SemanticCheck:
    cards = [object() for _ in range(4)]
    play = _plan(BalatroAction(PLAY_CARDS, cards=cards[:2]))
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=cards[2:]))

    class Evaluator:
        def project_play(self, state, action):
            del state, action
            return SimpleNamespace(expected_hand_score=10.0)

        def evaluate(self, state, action):
            del state
            return 8.0 if action.name == DISCARD_CARDS else 10.0

    policy = LiveHandActionPolicy(evaluator=Evaluator())
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=1,
        discards_remaining=3,
    )
    decision = policy.decide(state, (play, discard))
    return SemanticCheck(
        decision.mode == PACE_RECOVERY and decision.action is discard.action,
        observed=f"mode={decision.mode}, action={decision.action.name}",
        expected="with the final hand at risk, a useful discard preserves the scoring opportunity",
        detail=(
            "an under-pace Play consumes the last scoring hand while a discard does not; the canonical "
            "low-hand recovery bonus must preserve that survival distinction"
        ),
    )


def _public_draw_composition_ignores_hidden_order() -> SemanticCheck:
    cards = [
        BalatroCard("A", "Spades", live_id="a"),
        BalatroCard("K", "Hearts", live_id="k"),
        BalatroCard("Q", "Spades", live_id="q"),
        BalatroCard("7", "Clubs", live_id="7"),
    ]
    forward = PublicDeckComposition.from_cards(cards)
    reversed_order = PublicDeckComposition.from_cards(reversed(cards))
    same_items = forward.items() == reversed_order.items()
    same_spade_probability = abs(
        forward.probability_suit("Spades", draws=2)
        - reversed_order.probability_suit("Spades", draws=2)
    ) <= 1e-12
    return SemanticCheck(
        same_items and same_spade_probability,
        observed=(
            f"same_items={same_items}, same_spade_probability={same_spade_probability}, "
            f"p={forward.probability_suit('Spades', draws=2):.6f}"
        ),
        expected="public redraw probabilities are invariant to hidden deck-list ordering",
        detail=(
            "the live save may serialize the draw pile in an inaccessible order; D1 may use only the "
            "unordered public card composition, never hidden future draw identity or list position"
        ),
    )


def _consumable_clear_projection_keeps_use_as_first_action() -> SemanticCheck:
    consumable = object()
    action = BalatroAction(USE_CONSUMABLE, target=consumable)
    state = SimpleNamespace(hands_remaining=3, discards_remaining=2)
    recommendation = SimpleNamespace(
        before_projection=SimpleNamespace(
            joker_projection_complete=True,
            clears_blind=False,
        ),
        after_projection=SimpleNamespace(
            joker_projection_complete=True,
            clears_blind=True,
            expected_projected_total=120.0,
        ),
    )

    estimate = D1LiveBlindClearPlanner._estimate_from_recommendation(
        state,
        action,
        recommendation,
    )
    passed = bool(
        estimate is not None
        and estimate.action is action
        and estimate.action.name == USE_CONSUMABLE
        and estimate.exact
        and abs(estimate.value.clear_probability - 1.0) <= 1e-12
        and abs(estimate.value.expected_hands_remaining - 2.0) <= 1e-12
        and abs(estimate.value.expected_discards_remaining - 2.0) <= 1e-12
    )
    return SemanticCheck(
        passed,
        observed=(
            "none"
            if estimate is None
            else (
                f"action={estimate.action.name}, exact={estimate.exact}, "
                f"clear={estimate.value.clear_probability:.3f}, "
                f"hands={estimate.value.expected_hands_remaining:.1f}, "
                f"discards={estimate.value.expected_discards_remaining:.1f}"
            )
        ),
        expected="D1 may value the guaranteed follow-up clear while executing only USE_CONSUMABLE first",
        detail=(
            "the held consumable and its deterministic follow-up Play may be projected together for "
            "survival value, but execution must stop after the consumable, re-observe the authoritative "
            "checkpoint, and replan rather than chaining the hypothetical Play"
        ),
    )


RED_WHITE_PHASE1_D1_CASES = (
    SemanticBenchmarkCase(
        case_id="d1.survival.guaranteed_clear_preserves_discard",
        category="D1_SURVIVAL",
        description="guaranteed visible clears do not spend discard resources",
        evaluate=_guaranteed_clear_does_not_spend_discard,
        source="Phase 1 survival audit: resource-spend hierarchy",
    ),
    SemanticBenchmarkCase(
        case_id="d1.boss.recursive_cerulean_legality",
        category="D1_SURVIVAL",
        description="recursive D1 candidates preserve boss legality",
        evaluate=_recursive_cerulean_candidates_preserve_forced_legality,
        source="Phase 1 survival audit: root/recursive legality continuity",
    ),
    SemanticBenchmarkCase(
        case_id="d1.survival.underpace_prefers_material_redraw",
        category="D1_SURVIVAL",
        description="material redraw quality beats insufficient immediate score",
        evaluate=_underpace_play_yields_to_material_redraw,
        source="Phase 1 survival audit: redraw quality vs immediate score",
    ),
    SemanticBenchmarkCase(
        case_id="d1.resources.last_discard_marginal_recovery",
        category="D1_SURVIVAL",
        description="the final discard is not spent for a marginal recovery edge",
        evaluate=_last_discard_is_not_spent_for_marginal_recovery,
        source="Phase 1 survival audit: discard-resource hierarchy",
    ),
    SemanticBenchmarkCase(
        case_id="d1.timeout.latest_completed_root",
        category="D1_SURVIVAL",
        description="timeout reuses the latest fully completed canonical root",
        evaluate=_timeout_reuses_latest_completed_root,
        source="Phase 1 survival audit: partially completed adaptive search",
    ),
    SemanticBenchmarkCase(
        case_id="d1.timeout.sampled_clear_requires_confirmation",
        category="D1_SURVIVAL",
        description="timeout cannot promote an unconfirmed sampled clear",
        evaluate=_timeout_does_not_promote_unconfirmed_sampled_clear,
        source="Phase 1 survival audit: timeout confirmation boundary",
    ),
    SemanticBenchmarkCase(
        case_id="d1.resources.last_hand_prefers_recovery_discard",
        category="D1_SURVIVAL",
        description="last-hand recovery preserves the final scoring opportunity",
        evaluate=_last_hand_prefers_useful_discard_over_underpace_play,
        source="Phase 1 survival audit: hand-resource hierarchy",
    ),
    SemanticBenchmarkCase(
        case_id="d1.uncertainty.hidden_draw_order_invariant",
        category="D1_SURVIVAL",
        description="public draw projection is invariant to hidden deck ordering",
        evaluate=_public_draw_composition_ignores_hidden_order,
        source="Phase 1 survival audit: public-state uncertainty boundary",
    ),
    SemanticBenchmarkCase(
        case_id="d1.consumable.first_action_reobserve_boundary",
        category="D1_SURVIVAL",
        description="deterministic consumable clear projection preserves the re-observe boundary",
        evaluate=_consumable_clear_projection_keeps_use_as_first_action,
        source="Phase 1 survival audit: held-consumable use/replan boundary",
    ),
)
