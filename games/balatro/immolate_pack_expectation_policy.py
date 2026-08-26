from __future__ import annotations

"""Opened-pack Immolate choice from exact public-hand expectation."""

from games.balatro.build.immolate_expectation import ImmolateExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


IMMOLATE = "Immolate"


def install_immolate_pack_expectation_policy() -> None:
    if getattr(BalatroPackPolicy, "_immolate_pack_expectation_policy_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.immolate_expectation_evaluator = ImmolateExpectationEvaluator(
            target_evaluator=self.consumable_target_evaluator
        )

    def score_consumable(self, state, action, choice):
        if choice.kind != "SPECTRAL" or choice.label != IMMOLATE:
            return original_score_consumable(self, state, action, choice)

        expectation = self.immolate_expectation_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Immolate unavailable: fewer than five public hand cards",
                    *expectation.rationale,
                ),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Immolate deferred: public removal expectation incomplete",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Immolate does not beat the opened-pack skip baseline",
                    *expectation.rationale,
                ),
            )

        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                "Immolate uses analytic public-state destruction expectation",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy._immolate_pack_expectation_policy_installed = True
