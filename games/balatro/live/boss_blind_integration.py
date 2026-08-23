from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.card_selector import CardSelector
from games.balatro.live.cerulean_bell import CeruleanBellHandDecisionEvaluator
from games.balatro.live.crimson_heart import CrimsonHeartHandDecisionEvaluator
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.head_blind_planner import HeadHandDecisionEvaluator


@dataclass(frozen=True)
class BossBlindPlanningRule:
    """Planner-facing mechanics already validated for a live boss blind."""

    boss_name: str
    required_play_cards: int | None = None
    evaluator_factory: Callable[[], LiveHandDecisionEvaluator] | None = None


_BOSS_RULES = {
    # The Psychic debuffs any hand that does not contain exactly five played cards.
    # Treat those zero-score plays as inadmissible throughout recursive planning so
    # adaptive search cannot build a path through branches that Balatro will reject.
    "The Psychic": BossBlindPlanningRule(
        boss_name="The Psychic",
        required_play_cards=5,
    ),
    # Eye/Mouth conditions depend on mutable hand-type history and are represented
    # by the authoritative boss score transform.  Root D1 additionally removes
    # repeated Eye types while an unused legal type exists to reduce wasted search.
    "The Eye": BossBlindPlanningRule(
        boss_name="The Eye",
    ),
    "The Mouth": BossBlindPlanningRule(
        boss_name="The Mouth",
    ),
    # Card-debuff bosses are represented by Balatro's authoritative per-card
    # public ``debuff`` flag. The live observer reads that flag for the hand and
    # unordered deck composition, and public draw signatures preserve it through
    # hypothetical redraws. No boss-specific scorer is required here.
    "The Club": BossBlindPlanningRule(boss_name="The Club"),
    "The Goad": BossBlindPlanningRule(boss_name="The Goad"),
    "The Window": BossBlindPlanningRule(boss_name="The Window"),
    "The Plant": BossBlindPlanningRule(boss_name="The Plant"),
    "The Pillar": BossBlindPlanningRule(boss_name="The Pillar"),
    "The Head": BossBlindPlanningRule(
        boss_name="The Head",
        evaluator_factory=HeadHandDecisionEvaluator,
    ),
    # These four bosses alter only card visibility. Production process-memory
    # observation already exposes the underlying rank/suit identity, and the
    # project explicitly permits the agent to use it. Treat them as deterministic
    # pass-through rules rather than manufacturing uncertain hidden-card branches.
    "The House": BossBlindPlanningRule(boss_name="The House"),
    "The Wheel": BossBlindPlanningRule(boss_name="The Wheel"),
    "The Fish": BossBlindPlanningRule(boss_name="The Fish"),
    "The Mark": BossBlindPlanningRule(boss_name="The Mark"),
    # Finisher bosses. Amber Acorn's actual post-shuffle Joker order and Verdant
    # Leaf's card debuffs are already authoritative live state. Crimson Heart and
    # Cerulean Bell need narrow evaluator/action constraints.
    "Amber Acorn": BossBlindPlanningRule(boss_name="Amber Acorn"),
    "Verdant Leaf": BossBlindPlanningRule(boss_name="Verdant Leaf"),
    "Crimson Heart": BossBlindPlanningRule(
        boss_name="Crimson Heart",
        evaluator_factory=CrimsonHeartHandDecisionEvaluator,
    ),
    "Cerulean Bell": BossBlindPlanningRule(
        boss_name="Cerulean Bell",
        evaluator_factory=CeruleanBellHandDecisionEvaluator,
    ),
}


def boss_blind_planning_rule(state) -> BossBlindPlanningRule | None:
    if boss_blind_disabled_by_owned_jokers(state):
        return None

    boss_name = getattr(state, "boss_name", None)
    if boss_name is None:
        return None
    return _BOSS_RULES.get(str(boss_name))


def _same_card(left, right) -> bool:
    if left is right:
        return True
    left_id = getattr(left, "live_id", None)
    right_id = getattr(right, "live_id", None)
    return left_id is not None and left_id == right_id


def boss_play_action_is_legal(state, action) -> bool:
    """Return whether a Play/Discard action satisfies modeled boss constraints."""
    rule = boss_blind_planning_rule(state)
    if rule is None:
        return True
    if (
        rule.required_play_cards is not None
        and getattr(action, "name", None) == "PLAY_CARDS"
        and len(getattr(action, "cards", ())) != rule.required_play_cards
    ):
        return False

    if rule.boss_name == "Cerulean Bell":
        forced = [
            card
            for card in getattr(state, "hand", [])
            if bool(getattr(card, "forced_selection", False))
        ]
        if forced:
            selected = list(getattr(action, "cards", ()))
            return all(
                any(_same_card(card, candidate) for candidate in selected)
                for card in forced
            )

    return True


class BossAwareCardSelector(CardSelector):
    """Normal public-state action generation with modeled boss legality applied."""

    def generate_play_actions(self, state):
        return [
            action
            for action in super().generate_play_actions(state)
            if boss_play_action_is_legal(state, action)
        ]

    def generate_discard_actions(self, state):
        return [
            action
            for action in super().generate_discard_actions(state)
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
