from __future__ import annotations

"""Phase-1 semantic cases for Red/White D1 survival competence."""

from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as CoreD1LiveBlindClearPlanner,
)
from games.balatro.live.hand_action_policy import PACE_RECOVERY, LiveHandActionPolicy
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
        # Avoid constructing scorer/projector dependencies irrelevant to this
        # semantic. The inherited _candidate_actions logic is the behavior under test.
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


def _plan(action: BalatroAction, *, clear_probability: float = 0.10) -> LiveBlindPlan:
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
        exact=True,
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
)
