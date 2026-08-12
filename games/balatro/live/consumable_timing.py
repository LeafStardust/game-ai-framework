from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.actions import BalatroAction, USE_CONSUMABLE
from games.balatro.build import (
    ConsumableTargetEvaluation,
    ContextualConsumableTargetEvaluator,
)
from games.balatro.consumable import ConsumableContext
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator, LivePlayProjection


USE = "USE"
HOLD = "HOLD"


@dataclass(frozen=True)
class ConsumableTimingRecommendation:
    """B6 recommendation for using one held consumable on the current hand."""

    decision: str
    consumable: object
    target: ConsumableTargetEvaluation | None
    before_projection: LivePlayProjection | None
    after_projection: LivePlayProjection | None
    required_per_hand: float
    rationale: tuple[str, ...] = ()

    @property
    def should_use(self) -> bool:
        return self.decision == USE

    def to_action(self) -> BalatroAction | None:
        if not self.should_use or self.target is None:
            return None
        return BalatroAction(
            USE_CONSUMABLE,
            cards=list(self.target.cards),
            target=self.consumable,
        )


class LiveConsumableTimingPolicy:
    """Choose USE versus HOLD for deterministic targeted consumables.

    HOLD is the conservative baseline. A current-hand use is admitted only when
    public state shows a concrete timing benefit: better clear probability,
    restoring required blind pace, improving the final hand, or resolving full
    consumable-slot pressure with positive build-context target value and no
    immediate scoring regression.

    Exact card targets come from ``ContextualConsumableTargetEvaluator``. The
    transformation is simulated on a deep copy using the consumable's real
    ``can_use`` / ``use`` implementation, then normal visible-play projection is
    run before and after. No executor state is touched and no hidden draw order or
    RNG is consulted.
    """

    EPSILON = 1e-12

    def __init__(
        self,
        *,
        target_evaluator: ContextualConsumableTargetEvaluator | None = None,
        hand_evaluator: LiveHandDecisionEvaluator | None = None,
    ) -> None:
        self.target_evaluator = target_evaluator or ContextualConsumableTargetEvaluator()
        self.hand_evaluator = hand_evaluator or LiveHandDecisionEvaluator()

    def recommend(self, state, consumable: object) -> ConsumableTimingRecommendation:
        if getattr(state, "phase", None) != "SELECTING_HAND":
            return self._hold(state, consumable, "consumable timing requires SELECTING_HAND")

        consumable_index = self._identity_index(getattr(state, "consumables", ()), consumable)
        if consumable_index is None:
            return self._hold(state, consumable, "candidate consumable is not held")

        target = self.target_evaluator.recommend(state, consumable)
        if target is None:
            return self._hold(
                state,
                consumable,
                "no supported deterministic current-hand target",
            )

        before = self._best_play_projection(state)
        if before is None:
            return self._hold(state, consumable, "no legal visible play", target=target)
        if not before.joker_projection_complete:
            return self._hold(
                state,
                consumable,
                "current build has unsupported Joker score projection",
                target=target,
                before=before,
            )

        transformed = self._simulate_use(
            state,
            consumable_index=consumable_index,
            target_indices=target.target_indices,
        )
        if transformed is None:
            return self._hold(
                state,
                consumable,
                "target failed consumable can_use during copied simulation",
                target=target,
                before=before,
            )

        after = self._best_play_projection(transformed)
        if after is None:
            return self._hold(
                state,
                consumable,
                "consumable use leaves no legal visible play",
                target=target,
                before=before,
            )
        if not after.joker_projection_complete:
            return self._hold(
                state,
                consumable,
                "transformed build has unsupported Joker score projection",
                target=target,
                before=before,
                after=after,
            )

        required_per_hand = self._required_per_hand(state)
        decision_reason = self._use_reason(
            state,
            target=target,
            before=before,
            after=after,
            required_per_hand=required_per_hand,
        )

        rationale = (
            f"best-play clear probability {before.clear_probability:.6f} -> "
            f"{after.clear_probability:.6f}",
            f"best-play expected score {before.expected_hand_score:.3f} -> "
            f"{after.expected_hand_score:.3f}",
            f"required pace per remaining hand={required_per_hand:.3f}",
            f"target build-context delta={target.contextual_delta:.3f}",
            f"target total gain={target.total_gain:.3f}",
            *(target.rationale[:3]),
        )

        if decision_reason is None:
            return ConsumableTimingRecommendation(
                decision=HOLD,
                consumable=consumable,
                target=target,
                before_projection=before,
                after_projection=after,
                required_per_hand=required_per_hand,
                rationale=(
                    "HOLD: current use has no concrete timing advantage over preserving the consumable",
                    *rationale,
                ),
            )

        return ConsumableTimingRecommendation(
            decision=USE,
            consumable=consumable,
            target=target,
            before_projection=before,
            after_projection=after,
            required_per_hand=required_per_hand,
            rationale=(f"USE: {decision_reason}", *rationale),
        )

    def recommend_inventory(self, state) -> tuple[ConsumableTimingRecommendation, ...]:
        recommendations = [
            self.recommend(state, consumable)
            for consumable in getattr(state, "consumables", ())
        ]
        return tuple(
            sorted(
                recommendations,
                key=self._recommendation_key,
                reverse=True,
            )
        )

    def _use_reason(
        self,
        state,
        *,
        target: ConsumableTargetEvaluation,
        before: LivePlayProjection,
        after: LivePlayProjection,
        required_per_hand: float,
    ) -> str | None:
        if after.clear_probability > before.clear_probability + self.EPSILON:
            return "current target increases blind-clear probability"

        if (
            before.expected_hand_score + self.EPSILON < required_per_hand
            and after.expected_hand_score + self.EPSILON >= required_per_hand
        ):
            return "current target restores required blind pace"

        hands_remaining = max(0, int(getattr(state, "hands_remaining", 0)))
        if (
            hands_remaining <= 1
            and after.expected_hand_score > before.expected_hand_score + self.EPSILON
        ):
            return "final hand has positive immediate score gain"

        consumable_count = len(getattr(state, "consumables", ()))
        consumable_slots = max(0, int(getattr(state, "consumable_slots", 0)))
        slots_full = consumable_slots > 0 and consumable_count >= consumable_slots
        if (
            slots_full
            and target.contextual_delta > self.EPSILON
            and after.expected_hand_score + self.EPSILON >= before.expected_hand_score
        ):
            return "full consumable slots plus positive build-context target with no score regression"

        return None

    def _best_play_projection(self, state) -> LivePlayProjection | None:
        best: LivePlayProjection | None = None
        for action in self.hand_evaluator.action_generator.generate_play_actions(state):
            projection = self.hand_evaluator.project_play(state, action)
            if best is None or self._projection_key(projection) > self._projection_key(best):
                best = projection
        return best

    def _simulate_use(
        self,
        state,
        *,
        consumable_index: int,
        target_indices: tuple[int, ...],
    ):
        simulated = copy.deepcopy(state)
        if not (0 <= consumable_index < len(simulated.consumables)):
            return None
        if any(index < 0 or index >= len(simulated.hand) for index in target_indices):
            return None

        consumable = simulated.consumables[consumable_index]
        cards = [simulated.hand[index] for index in target_indices]
        context = ConsumableContext(state=simulated, cards=cards)
        if not consumable.can_use(context):
            return None

        consumable.use(context)
        simulated.consumables.pop(consumable_index)
        return simulated

    def _hold(
        self,
        state,
        consumable: object,
        reason: str,
        *,
        target: ConsumableTargetEvaluation | None = None,
        before: LivePlayProjection | None = None,
        after: LivePlayProjection | None = None,
    ) -> ConsumableTimingRecommendation:
        return ConsumableTimingRecommendation(
            decision=HOLD,
            consumable=consumable,
            target=target,
            before_projection=before,
            after_projection=after,
            required_per_hand=self._required_per_hand(state),
            rationale=(f"HOLD: {reason}",),
        )

    @staticmethod
    def _required_per_hand(state) -> float:
        requirement = int(getattr(getattr(state, "blind", None), "requirement", 0))
        remaining = max(0.0, float(requirement - int(getattr(state, "score", 0))))
        hands = max(1, int(getattr(state, "hands_remaining", 1)))
        return remaining / hands

    @staticmethod
    def _identity_index(items, candidate: object) -> int | None:
        for index, item in enumerate(items):
            if item is candidate:
                return index
        return None

    @staticmethod
    def _projection_key(projection: LivePlayProjection) -> tuple[float, ...]:
        return (
            float(projection.clear_probability),
            float(projection.expected_hand_score),
            float(projection.hand_score),
            float(projection.maximum_hand_score),
        )

    @staticmethod
    def _recommendation_key(recommendation: ConsumableTimingRecommendation) -> tuple:
        target_gain = recommendation.target.total_gain if recommendation.target is not None else float("-inf")
        after_clear = (
            recommendation.after_projection.clear_probability
            if recommendation.after_projection is not None
            else 0.0
        )
        after_score = (
            recommendation.after_projection.expected_hand_score
            if recommendation.after_projection is not None
            else 0.0
        )
        return (
            1 if recommendation.should_use else 0,
            float(after_clear),
            float(after_score),
            float(target_gain),
            str(getattr(recommendation.consumable, "name", "")),
        )
