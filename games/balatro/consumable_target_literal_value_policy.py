from __future__ import annotations

import copy
from dataclasses import replace

from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator
from games.balatro.consumable import ConsumableContext


def install_consumable_target_literal_value_policy() -> None:
    """Make default deterministic consumable targeting use literal modeled value.

    ``effective_changes`` remains a legality/no-op guard and an explainable field,
    but merely changing a public card property is not itself Balatro value. Keep
    the evaluator's explicit constructor override for experiments/legacy callers;
    only the production/default value changes from the historical synthetic 0.10
    per transformed card to 0.0.

    The target evaluator's existing intrinsic card scale is still real modeled
    value: a Steel/Glass/rank upgrade changes the public card itself. Preserve that
    before->after intrinsic delta for deterministic Tarot transforms just as Death
    and targeted Spectral seals already do. This is distinct from the retired
    generic "a property changed" bonus.
    """
    if getattr(
        ContextualConsumableTargetEvaluator,
        "_literal_change_value_installed",
        False,
    ):
        return

    original_init = ContextualConsumableTargetEvaluator.__init__
    original_evaluate_target = ContextualConsumableTargetEvaluator._evaluate_target

    def literal_init(
        self,
        *,
        profiler=None,
        card_evaluator=None,
        effective_change_value: float = 0.0,
        enhancement_overwrite_penalty: float = 0.35,
        deck_thinning_value: float = 0.05,
    ) -> None:
        original_init(
            self,
            profiler=profiler,
            card_evaluator=card_evaluator,
            effective_change_value=effective_change_value,
            enhancement_overwrite_penalty=enhancement_overwrite_penalty,
            deck_thinning_value=deck_thinning_value,
        )

    def literal_evaluate_target(self, state, consumable, indices, *, profile):
        evaluation = original_evaluate_target(
            self,
            state,
            consumable,
            indices,
            profile=profile,
        )
        if evaluation is None:
            return None

        category = str(getattr(consumable, "category", "")).upper()
        name = str(getattr(consumable, "name", ""))
        if category != "TAROT" or name == "Death":
            return evaluation

        simulated_state = copy.deepcopy(state)
        simulated_consumable = copy.deepcopy(consumable)
        try:
            simulated_cards = [simulated_state.hand[index] for index in indices]
        except (AttributeError, IndexError, TypeError):
            return evaluation
        before_cards = [copy.deepcopy(card) for card in simulated_cards]
        context = ConsumableContext(state=simulated_state, cards=simulated_cards)
        try:
            if not simulated_consumable.can_use(context):
                return evaluation
            simulated_consumable.use(context)
        except (AttributeError, KeyError, TypeError, ValueError):
            return evaluation

        intrinsic_delta = sum(
            self._card_intrinsic_value(after) - self._card_intrinsic_value(before)
            for before, after in zip(before_cards, simulated_cards)
        )
        if abs(float(intrinsic_delta)) <= 1e-12:
            return evaluation

        return replace(
            evaluation,
            total_gain=float(evaluation.total_gain) + float(intrinsic_delta),
            intrinsic_delta=float(evaluation.intrinsic_delta) + float(intrinsic_delta),
            rationale=(
                *tuple(evaluation.rationale),
                f"literal Tarot card-property intrinsic delta={float(intrinsic_delta):.3f}",
                "generic effective-change bonus remains zero",
            ),
        )

    ContextualConsumableTargetEvaluator.__init__ = literal_init
    ContextualConsumableTargetEvaluator._evaluate_target = literal_evaluate_target
    ContextualConsumableTargetEvaluator._literal_change_value_installed = True
