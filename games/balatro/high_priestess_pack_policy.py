from __future__ import annotations

"""Opened-pack High Priestess expectation over the public Planet pool."""

from games.balatro.build.high_priestess_expectation import HighPriestessExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


HIGH_PRIESTESS = "The High Priestess"


def install_high_priestess_pack_policy() -> None:
    if getattr(BalatroPackPolicy, "_high_priestess_pack_policy_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.high_priestess_evaluator = HighPriestessExpectationEvaluator(
            item_estimator=self.item_estimator
        )

    def score_consumable(self, state, action, choice):
        if choice.kind != "TAROT" or choice.label != HIGH_PRIESTESS:
            return original_score_consumable(self, state, action, choice)

        expectation = self.high_priestess_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                (
                    "High Priestess unavailable: generated Planets require free consumable capacity",
                    *expectation.rationale,
                ),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "High Priestess deferred: public Planet expectation incomplete",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "High Priestess has no positive modeled generated-Planet value",
                    *expectation.rationale,
                ),
            )

        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                "High Priestess uses analytic public-state Planet expectation; no RNG sample or seed read",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS) | {HIGH_PRIESTESS}
    )
    BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS) - {HIGH_PRIESTESS}
    )
    BalatroPackPolicy._high_priestess_pack_policy_installed = True
