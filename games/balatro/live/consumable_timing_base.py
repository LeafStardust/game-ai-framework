from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.actions import BalatroAction, USE_CONSUMABLE
from games.balatro.build import (
    ConsumableTargetEvaluation,
    ContextualConsumableTargetEvaluator,
)
from games.balatro.consumable import ConsumableContext
from games.balatro.live.consumable_factory import LiveConsumableFactory
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
    immediate_gain: float = 0.0
    rationale: tuple[str, ...] = ()

    @property
    def should_use(self) -> bool:
        return self.decision == USE

    def to_action(self) -> BalatroAction | None:
        if not self.should_use:
            return None
        return BalatroAction(
            USE_CONSUMABLE,
            cards=list(self.target.cards) if self.target is not None else [],
            target=self.consumable,
        )


class LiveConsumableTimingPolicy:
    """Choose USE versus HOLD for deterministic held consumables.

    Targeted transformations use the existing B6 target-quality and visible-hand
    projection path. Deterministic no-target economy Tarots and Planets are timed
    from their exact public effects. The Fool resolves only Balatro's public
    ``last_tarot_planet`` key and is spent only when the copied modeled consumable
    itself has a concrete current timing reason. No executor state is touched and
    no hidden draw order or RNG is consulted.
    """

    EPSILON = 1e-12
    ECONOMY_TAROTS = frozenset({"The Hermit", "Temperance"})

    def __init__(
        self,
        *,
        target_evaluator: ContextualConsumableTargetEvaluator | None = None,
        hand_evaluator: LiveHandDecisionEvaluator | None = None,
        consumable_factory: LiveConsumableFactory | None = None,
    ) -> None:
        self.target_evaluator = target_evaluator or ContextualConsumableTargetEvaluator()
        self.hand_evaluator = hand_evaluator or LiveHandDecisionEvaluator()
        self.consumable_factory = consumable_factory or LiveConsumableFactory()

    def recommend(self, state, consumable: object) -> ConsumableTimingRecommendation:
        if getattr(state, "phase", None) != "SELECTING_HAND":
            return self._hold(state, consumable, "consumable timing requires SELECTING_HAND")

        consumable_index = self._identity_index(getattr(state, "consumables", ()), consumable)
        if consumable_index is None:
            return self._hold(state, consumable, "candidate consumable is not held")

        name = str(getattr(consumable, "name", ""))
        category = str(getattr(consumable, "category", "")).upper()
        if name == "The Fool":
            return self._recommend_fool(
                state,
                consumable,
                consumable_index=consumable_index,
            )
        if category == "PLANET":
            return self._recommend_planet(
                state,
                consumable,
                consumable_index=consumable_index,
            )
        if name in self.ECONOMY_TAROTS:
            return self._recommend_economy(state, consumable, name=name)

        ranked_targets = self.target_evaluator.rank_targets(state, consumable)
        target = ranked_targets[0] if ranked_targets else None
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
        if name == "The Hanged Man":
            decision_reason = self._hanged_man_use_reason(
                state,
                target=target,
                ranked_targets=ranked_targets,
                before=before,
                after=after,
            )
        else:
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

    def _recommend_fool(
        self,
        state,
        consumable: object,
        *,
        consumable_index: int,
    ) -> ConsumableTimingRecommendation:
        last_key = getattr(state, "last_tarot_planet", None)
        if not isinstance(last_key, str) or not last_key:
            return self._hold(
                state,
                consumable,
                "Fool has no previous Tarot/Planet in public run history",
            )
        if last_key == "c_fool":
            return self._hold(
                state,
                consumable,
                "Fool cannot copy The Fool",
            )

        copied = self.consumable_factory.create({"key": last_key})
        if copied is None:
            return self._hold(
                state,
                consumable,
                f"Fool copy target {last_key!r} is not modeled",
            )

        copied_name = str(getattr(copied, "name", type(copied).__name__))
        copied_category = str(getattr(copied, "category", "")).upper()
        if copied_name == "The Fool" or copied_category not in {"TAROT", "PLANET"}:
            return self._hold(
                state,
                consumable,
                f"Fool copy target {last_key!r} is invalid",
            )

        converted = copy.deepcopy(state)
        if not (0 <= consumable_index < len(converted.consumables)):
            return self._hold(state, consumable, "Fool inventory slot became unavailable")
        converted.consumables[consumable_index] = copied
        converted.last_tarot_planet = last_key

        copied_timing = self.recommend(converted, copied)
        if not copied_timing.should_use:
            return ConsumableTimingRecommendation(
                decision=HOLD,
                consumable=consumable,
                target=None,
                before_projection=None,
                after_projection=None,
                required_per_hand=self._required_per_hand(state),
                rationale=(
                    f"HOLD: Fool copy target {copied_name} has no concrete modeled use now",
                    f"last_tarot_planet={last_key}",
                    *copied_timing.rationale[:4],
                ),
            )

        return ConsumableTimingRecommendation(
            decision=USE,
            consumable=consumable,
            target=None,
            before_projection=None,
            after_projection=None,
            required_per_hand=self._required_per_hand(state),
            rationale=(
                f"USE: materialize public Fool copy target {copied_name} for a concrete next-step use",
                f"last_tarot_planet={last_key}",
                "follow-up action chaining remains disabled; copied consumable requires fresh observation",
                *copied_timing.rationale[:4],
            ),
        )

    def _recommend_planet(
        self,
        state,
        consumable: object,
        *,
        consumable_index: int,
    ) -> ConsumableTimingRecommendation:
        before = self._best_play_projection(state)
        if before is None:
            return self._hold(state, consumable, "no legal visible play for Planet timing")
        if not before.joker_projection_complete:
            return self._hold(
                state,
                consumable,
                "current build has unsupported Joker score projection",
                before=before,
            )

        transformed = self._simulate_use(
            state,
            consumable_index=consumable_index,
            target_indices=(),
        )
        if transformed is None:
            return self._hold(
                state,
                consumable,
                "Planet failed deterministic copied simulation",
                before=before,
            )

        after = self._best_play_projection(transformed)
        if after is None:
            return self._hold(
                state,
                consumable,
                "Planet use leaves no legal visible play",
                before=before,
            )
        if not after.joker_projection_complete:
            return self._hold(
                state,
                consumable,
                "Planet-upgraded build has unsupported Joker score projection",
                before=before,
                after=after,
            )

        required = self._required_per_hand(state)
        reason = self._planet_use_reason(
            state,
            before=before,
            after=after,
            required_per_hand=required,
        )
        name = str(getattr(consumable, "name", "Planet"))
        hand_type = str(getattr(consumable, "hand_type", "unknown"))
        before_level = int(getattr(state, "hand_levels", {}).get(hand_type, 0))
        after_level = int(getattr(transformed, "hand_levels", {}).get(hand_type, 0))
        rationale = (
            f"Planet={name} hand={hand_type} level {before_level} -> {after_level}",
            f"best-play clear probability {before.clear_probability:.6f} -> {after.clear_probability:.6f}",
            f"best-play expected score {before.expected_hand_score:.3f} -> {after.expected_hand_score:.3f}",
            f"required pace per remaining hand={required:.3f}",
        )

        if reason is None:
            return ConsumableTimingRecommendation(
                decision=HOLD,
                consumable=consumable,
                target=None,
                before_projection=before,
                after_projection=after,
                required_per_hand=required,
                rationale=(
                    "HOLD: Planet upgrade has no concrete current timing advantage",
                    *rationale,
                ),
            )

        return ConsumableTimingRecommendation(
            decision=USE,
            consumable=consumable,
            target=None,
            before_projection=before,
            after_projection=after,
            required_per_hand=required,
            rationale=(f"USE: {reason}", *rationale),
        )

    def _recommend_economy(
        self,
        state,
        consumable: object,
        *,
        name: str,
    ) -> ConsumableTimingRecommendation:
        slots_full = self._consumable_slots_full(state)
        required = self._required_per_hand(state)

        if name == "The Hermit":
            money = max(0, int(getattr(state, "money", 0)))
            gain = max(0, min(money * 2, 20) - money)
            if gain <= 0:
                return self._hold(
                    state,
                    consumable,
                    "Hermit has no positive deterministic money gain",
                    immediate_gain=0.0,
                )

            if 10 <= money < 20:
                reason = "Hermit is at or past its maximum-value $10 threshold"
                decision = USE
            elif slots_full:
                reason = "full consumable slots plus positive deterministic Hermit gain"
                decision = USE
            else:
                reason = "Hermit is below $10, so preserving it can increase deterministic payout"
                decision = HOLD

            return ConsumableTimingRecommendation(
                decision=decision,
                consumable=consumable,
                target=None,
                before_projection=None,
                after_projection=None,
                required_per_hand=required,
                immediate_gain=float(gain),
                rationale=(
                    f"{decision}: {reason}",
                    f"Hermit money ${money} -> ${money + gain}",
                    f"deterministic money gain=${gain}",
                    f"consumable slots full={slots_full}",
                ),
            )

        payout = self._temperance_payout(state)
        if payout <= 0:
            return self._hold(
                state,
                consumable,
                "Temperance has no positive deterministic Joker sell-value payout",
                immediate_gain=0.0,
            )

        if payout >= 50:
            reason = "Temperance has reached its $50 payout cap"
            decision = USE
        elif slots_full:
            reason = "full consumable slots plus positive deterministic Temperance payout"
            decision = USE
        else:
            reason = "Temperance is below its $50 cap, so preserving it keeps higher future payout optionality"
            decision = HOLD

        return ConsumableTimingRecommendation(
            decision=decision,
            consumable=consumable,
            target=None,
            before_projection=None,
            after_projection=None,
            required_per_hand=required,
            immediate_gain=float(payout),
            rationale=(
                f"{decision}: {reason}",
                f"deterministic Temperance payout=${payout}",
                f"consumable slots full={slots_full}",
            ),
        )

    def _hanged_man_use_reason(
        self,
        state,
        *,
        target: ConsumableTargetEvaluation,
        ranked_targets: tuple[ConsumableTargetEvaluation, ...],
        before: LivePlayProjection,
        after: LivePlayProjection,
    ) -> str | None:
        if target.total_gain <= self.EPSILON:
            return None
        if after.expected_hand_score + self.EPSILON < before.expected_hand_score:
            return None

        positive_single_indices = {
            evaluation.target_indices[0]
            for evaluation in ranked_targets
            if (
                len(evaluation.target_indices) == 1
                and evaluation.total_gain > self.EPSILON
            )
        }
        if (
            len(target.target_indices) == 2
            and all(index in positive_single_indices for index in target.target_indices)
        ):
            return (
                "best public Hanged Man target removes two independently "
                "positive deck-thinning cards with no current-play regression"
            )

        if self._consumable_slots_full(state):
            return (
                "full consumable slots plus positive Hanged Man deck-thinning "
                "target with no current-play regression"
            )

        return None

    def _planet_use_reason(
        self,
        state,
        *,
        before: LivePlayProjection,
        after: LivePlayProjection,
        required_per_hand: float,
    ) -> str | None:
        if after.clear_probability > before.clear_probability + self.EPSILON:
            return "Planet upgrade increases blind-clear probability"
        if (
            before.expected_hand_score + self.EPSILON < required_per_hand
            and after.expected_hand_score + self.EPSILON >= required_per_hand
        ):
            return "Planet upgrade restores required blind pace"
        hands_remaining = max(0, int(getattr(state, "hands_remaining", 0)))
        if (
            hands_remaining <= 1
            and after.expected_hand_score > before.expected_hand_score + self.EPSILON
        ):
            return "final hand gains score from deterministic Planet upgrade"
        if (
            self._consumable_slots_full(state)
            and after.expected_hand_score + self.EPSILON >= before.expected_hand_score
        ):
            return "full consumable slots plus permanent Planet upgrade with no score regression"
        return None

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

        if (
            self._consumable_slots_full(state)
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

        if str(getattr(consumable, "name", "")) == "The Hanged Man":
            destroyed_ids = {id(card) for card in cards}
            simulated.discard_pile = [
                card
                for card in getattr(simulated, "discard_pile", ())
                if id(card) not in destroyed_ids
            ]
            if not self._remove_from_owned_deck(simulated, cards):
                return None

        simulated.consumables.pop(consumable_index)
        return simulated

    @staticmethod
    def _remove_from_owned_deck(state, cards: list[object]) -> bool:
        owned_deck = getattr(state, "owned_deck", None)
        if owned_deck is None:
            return False

        remaining = list(owned_deck)
        for card in cards:
            live_id = getattr(card, "live_id", None)
            if live_id is None:
                return False

            matches = [
                index
                for index, owned_card in enumerate(remaining)
                if getattr(owned_card, "live_id", None) == live_id
            ]
            if len(matches) != 1:
                return False

            index = matches[0]
            remaining[index] = None

        state.owned_deck = [
            card
            for card in remaining
            if card is not None
        ]
        return True

    def _hold(
        self,
        state,
        consumable: object,
        reason: str,
        *,
        target: ConsumableTargetEvaluation | None = None,
        before: LivePlayProjection | None = None,
        after: LivePlayProjection | None = None,
        immediate_gain: float = 0.0,
    ) -> ConsumableTimingRecommendation:
        return ConsumableTimingRecommendation(
            decision=HOLD,
            consumable=consumable,
            target=target,
            before_projection=before,
            after_projection=after,
            required_per_hand=self._required_per_hand(state),
            immediate_gain=float(immediate_gain),
            rationale=(f"HOLD: {reason}",),
        )

    @staticmethod
    def _temperance_payout(state) -> int:
        total = 0.0
        for joker in getattr(state, "jokers", ()):
            value = getattr(joker, "sell_cost", None)
            if value is None:
                value = getattr(joker, "sell_value", 0)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            total += max(0.0, float(value))
        return int(min(total, 50.0))

    @staticmethod
    def _consumable_slots_full(state) -> bool:
        count = len(getattr(state, "consumables", ()))
        slots = max(0, int(getattr(state, "consumable_slots", 0)))
        return slots > 0 and count >= slots

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
            float(recommendation.immediate_gain),
            float(target_gain),
            str(getattr(recommendation.consumable, "name", "")),
        )
