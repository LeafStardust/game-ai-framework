from __future__ import annotations

"""Opened-pack policy for Familiar, Grim, and Incantation.

These effects have finite public random outcome spaces. Their expected value comes
from ``GeneratedEnhancedSpectralExpectationEvaluator`` rather than a fixed Spectral
bonus or generic shop-consumable category score.
"""

from games.balatro.build.generated_enhanced_spectral_expectation import (
    GeneratedEnhancedSpectralExpectationEvaluator,
    SPECS,
)
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


_MODELED = frozenset(SPECS)


def install_generated_enhanced_spectral_pack_policy() -> None:
    if getattr(
        BalatroPackPolicy,
        "_generated_enhanced_spectral_pack_policy_installed",
        False,
    ):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.generated_enhanced_spectral_expectation_evaluator = (
            GeneratedEnhancedSpectralExpectationEvaluator(
                target_evaluator=self.consumable_target_evaluator
            )
        )

    def score_consumable(self, state, action, choice):
        if choice.kind != "SPECTRAL" or choice.label not in _MODELED:
            return original_score_consumable(self, state, action, choice)

        expectation = self.generated_enhanced_spectral_expectation_evaluator.evaluate(
            state,
            choice.label,
        )
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                (
                    f"{choice.label} unavailable in current public hand",
                    *expectation.rationale,
                ),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    f"{choice.label} deferred: public expectation incomplete",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    f"{choice.label} does not beat the opened-pack skip baseline",
                    *expectation.rationale,
                ),
            )

        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                f"{choice.label} uses analytic public generated-card expectation",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    # Keep classification/introspection aligned with the installed production
    # authority. These cards were historically left in DEFERRED_SPECTRALS even
    # after their complete analytic expectation path became authoritative.
    BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS) | set(_MODELED)
    )
    BalatroPackPolicy.DEFERRED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.DEFERRED_SPECTRALS) - set(_MODELED)
    )
    BalatroPackPolicy._generated_enhanced_spectral_pack_policy_installed = True
