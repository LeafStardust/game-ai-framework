from __future__ import annotations

from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator


def install_consumable_target_literal_value_policy() -> None:
    """Make default deterministic consumable targeting use literal modeled value.

    ``effective_changes`` remains a legality/no-op guard and an explainable field,
    but merely changing a public card property is not itself Balatro value. Keep
    the evaluator's explicit constructor override for experiments/legacy callers;
    only the production/default value changes from the historical synthetic 0.10
    per transformed card to 0.0.

    Target value continues to come from contextual build interaction plus the
    explicit effect-specific models already owned by Death, Spectral seals, thinning,
    and other dedicated policies. Do not add a generic Tarot card-property bonus here.
    Canonical whole-build strategic adjustment is installed after this literal-value
    correction so it remains downstream of legality and effect-specific mechanics.
    """
    if not getattr(
        ContextualConsumableTargetEvaluator,
        "_literal_change_value_installed",
        False,
    ):
        original_init = ContextualConsumableTargetEvaluator.__init__

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

        ContextualConsumableTargetEvaluator.__init__ = literal_init
        ContextualConsumableTargetEvaluator._literal_change_value_installed = True

    from games.balatro.consumable_strategy_delta_policy import (
        install_consumable_strategy_delta_policy,
    )

    install_consumable_strategy_delta_policy()
