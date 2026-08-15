from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from games.balatro.card_selector import CardSelector
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.head_blind_planner import HeadHandDecisionEvaluator


@dataclass(frozen=True)
class BossBlindPlanningRule:
    """Planner-facing mechanics already validated for a live boss blind."""

    boss_name: str
    required_play_cards: int | None = None
    evaluator_factory: Callable[[], LiveHandDecisionEvaluator] | None = None


_BOSS_RULES = {
    "The Psychic": BossBlindPlanningRule(
        boss_name="The Psychic",
        required_play_cards=5,
    ),
    "The Head": BossBlindPlanningRule(
        boss_name="The Head",
        evaluator_factory=HeadHandDecisionEvaluator,
    ),
    "The House": BossBlindPlanningRule(
        boss_name="The House",
    ),
}


def boss_blind_planning_rule(state) -> BossBlindPlanningRule | None:
    boss_name = getattr(state, "boss_name", None)
    if boss_name is None:
        return None
    return _BOSS_RULES.get(str(boss_name))


def boss_play_action_is_legal(state, action) -> bool:
    """Return whether a Play action satisfies modeled boss-specific legality."""
    rule = boss_blind_planning_rule(state)
    if rule is None or rule.required_play_cards is None:
        return True
    return len(getattr(action, "cards", ())) == rule.required_play_cards


class BossAwareCardSelector(CardSelector):
    """Normal public-state action generation with modeled boss legality applied."""

    def generate_play_actions(self, state):
        return [
            action
            for action in super().generate_play_actions(state)
            if boss_play_action_is_legal(state, action)
        ]


class BossAwareLiveHandDecisionEvaluator(LiveHandDecisionEvaluator):
    """Dispatch score/evaluation semantics to validated boss-specific evaluators."""

    def __init__(self):
        super().__init__()
        self.action_generator = BossAwareCardSelector()
        self._boss_evaluators: dict[str, LiveHandDecisionEvaluator] = {}

    def evaluator_for_state(self, state) -> LiveHandDecisionEvaluator:
        rule = boss_blind_planning_rule(state)
        if rule is None or rule.evaluator_factory is None:
            return self

        evaluator = self._boss_evaluators.get(rule.boss_name)
        if evaluator is None:
            evaluator = rule.evaluator_factory()
            evaluator.action_generator = self.action_generator
            self._boss_evaluators[rule.boss_name] = evaluator
        return evaluator

    def evaluate(self, state, action) -> float:
        evaluator = self.evaluator_for_state(state)
        if evaluator is self:
            return super().evaluate(state, action)
        return evaluator.evaluate(state, action)

    def project_play(self, state, action):
        evaluator = self.evaluator_for_state(state)
        if evaluator is self:
            return super().project_play(state, action)
        return evaluator.project_play(state, action)
