from __future__ import annotations

"""Phase-1 semantic cases for Red/White D1 survival competence."""

from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as CoreD1LiveBlindClearPlanner,
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
)
