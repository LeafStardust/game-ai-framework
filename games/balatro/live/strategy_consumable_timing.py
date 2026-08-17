from __future__ import annotations

import copy
from dataclasses import replace

from games.balatro.consumable import ConsumableContext
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.strategy import BalatroStrategyTracker


class StrategyAwareConsumableTargetEvaluator:
    """D6 tie-breaker for already-legal deterministic consumable targets.

    The wrapped B6/D6 evaluator remains authoritative for legality and target
    quality. Universal strategy is consulted only after equal total gain and
    equal effective-change count, so it cannot rescue an inferior target.
    """

    def __init__(self, base_evaluator, *, strategy_tracker: BalatroStrategyTracker) -> None:
        self.base_evaluator = base_evaluator
        self.strategy_tracker = strategy_tracker

    def supports(self, consumable: object) -> bool:
        return bool(self.base_evaluator.supports(consumable))

    def recommend(self, state, consumable: object):
        ranked = self.rank_targets(state, consumable)
        return ranked[0] if ranked else None

    def rank_targets(self, state, consumable: object):
        ranked = tuple(self.base_evaluator.rank_targets(state, consumable))
        if len(ranked) <= 1:
            return ranked

        resolution = self.strategy_tracker.observe(state)
        if resolution.dominant_strategy_id is None:
            return ranked

        strategy_fit = {
            evaluation.target_indices: self._strategy_target_fit(
                state,
                consumable,
                evaluation.target_indices,
                resolution,
            )
            for evaluation in ranked
        }
        return tuple(
            sorted(
                ranked,
                key=lambda evaluation: (
                    -float(evaluation.total_gain),
                    -int(evaluation.effective_changes),
                    -float(strategy_fit.get(evaluation.target_indices, 0.0)),
                    evaluation.target_indices,
                ),
            )
        )

    def _strategy_target_fit(
        self,
        state,
        consumable: object,
        target_indices: tuple[int, ...],
        resolution,
    ) -> float:
        # Hanged Man's strategic effect is deck removal rather than a surviving
        # transformed card. Keep its mature deck-thinning evaluator authoritative.
        if str(getattr(consumable, "name", "")) == "The Hanged Man":
            return 0.0

        simulated_state = copy.deepcopy(state)
        simulated_consumable = copy.deepcopy(consumable)
        hand = list(getattr(simulated_state, "hand", ()))
        if any(index < 0 or index >= len(hand) for index in target_indices):
            return 0.0

        transformed_cards = [hand[index] for index in target_indices]
        before_cards = [copy.deepcopy(card) for card in transformed_cards]
        context = ConsumableContext(state=simulated_state, cards=transformed_cards)
        if not simulated_consumable.can_use(context):
            return 0.0
        simulated_consumable.use(context)

        assessment_by_id = {
            assessment.strategy_id: assessment
            for assessment in resolution.assessments
        }
        shortlist = (
            resolution.dominant_strategy_id,
            *resolution.relevant_strategy_ids,
        )
        dominant = assessment_by_id.get(resolution.dominant_strategy_id)
        dominant_score = max(0.0, float(getattr(dominant, "score", 0.0)))
        if dominant_score <= 0.0:
            return 0.0

        total = 0.0
        for strategy_id in shortlist:
            if strategy_id is None:
                continue
            definition = self.strategy_tracker.definitions.get(strategy_id)
            assessment = assessment_by_id.get(strategy_id)
            if definition is None or assessment is None:
                continue
            score = max(0.0, float(assessment.score))
            if score <= 0.0:
                continue
            relative_strength = min(1.0, score / dominant_score)
            before_fit = sum(self._card_fit(card, definition) for card in before_cards)
            after_fit = sum(self._card_fit(card, definition) for card in transformed_cards)
            total += (after_fit - before_fit) * relative_strength
        return total

    @staticmethod
    def _card_fit(card, definition) -> float:
        fit = 0.0
        suit = str(getattr(card, "suit", ""))
        rank = str(getattr(card, "rank", ""))
        enhancement = str(getattr(card, "enhancement", ""))
        seal = str(getattr(card, "seal", ""))
        edition = str(getattr(card, "edition", ""))

        if suit and suit in definition.preferred_suits:
            fit += 1.0
        if enhancement and enhancement in definition.preferred_enhancements:
            fit += 1.0
        if seal and seal in definition.preferred_seals:
            fit += 1.0
        if edition and edition in definition.preferred_editions:
            fit += 1.0
        if rank and rank in definition.preferred_ranks:
            fit += 1.0

        face_mode = str(getattr(definition, "face_mode", "") or "").upper()
        if face_mode:
            is_face = rank in {"J", "Q", "K"}
            if (face_mode == "FACE" and is_face) or (
                face_mode == "FACELESS" and not is_face
            ):
                fit += 1.0
        return fit


class StrategyAwareLiveConsumableTimingPolicy(LiveConsumableTimingPolicy):
    """D5/D6 universal-strategy layer beneath tactical consumable safety.

    Existing USE/HOLD admission, blind-clear delegation, target quality, and
    playbook thresholds remain authoritative. Strategy only breaks otherwise
    equal live USE choices and otherwise equal legal target choices.
    """

    def __init__(self, *, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self.strategy_tracker = strategy_tracker

    @classmethod
    def from_policy(
        cls,
        policy: LiveConsumableTimingPolicy,
        *,
        strategy_tracker: BalatroStrategyTracker,
        planet_policy=None,
    ) -> "StrategyAwareLiveConsumableTimingPolicy":
        return cls(
            strategy_tracker=strategy_tracker,
            target_evaluator=StrategyAwareConsumableTargetEvaluator(
                policy.target_evaluator,
                strategy_tracker=strategy_tracker,
            ),
            hand_evaluator=policy.hand_evaluator,
            consumable_factory=policy.consumable_factory,
            wheel_evaluator=policy.wheel_evaluator,
            planet_policy=planet_policy or policy.planet_policy,
            use_thresholds=policy.use_thresholds,
            target_thresholds=policy.target_thresholds,
            defer_blind_clear_to_d1=policy.defer_blind_clear_to_d1,
        )

    def recommend_inventory(self, state):
        recommendations = tuple(super().recommend_inventory(state))
        if len(recommendations) <= 1:
            return recommendations

        fits = {
            id(recommendation): self._strategy_use_fit(state, recommendation)
            for recommendation in recommendations
        }
        annotated = tuple(
            replace(
                recommendation,
                rationale=(
                    *recommendation.rationale,
                    f"D5 universal-strategy use fit={fits[id(recommendation)]:+.6f}",
                ),
            )
            for recommendation in recommendations
        )
        return tuple(
            sorted(
                annotated,
                key=lambda recommendation: self._strategy_recommendation_key(
                    recommendation,
                    fits[id(recommendation)],
                ),
                reverse=True,
            )
        )

    def _strategy_use_fit(self, state, recommendation) -> float:
        if not recommendation.should_use:
            return 0.0
        category = str(getattr(recommendation.consumable, "category", "")).upper()
        if category not in {"TAROT", "SPECTRAL"}:
            return 0.0
        evaluation = self.strategy_tracker.evaluate_item(
            state,
            recommendation.consumable,
            kind="CONSUMABLE",
        )
        return float(evaluation.value)

    def _strategy_recommendation_key(self, recommendation, strategy_fit: float) -> tuple:
        base = self._recommendation_key(recommendation)
        # The existing deterministic/tactical key remains entirely ahead of
        # strategy. Only its final lexical name tie-break moves behind strategy.
        return (*base[:-1], float(strategy_fit), base[-1])
