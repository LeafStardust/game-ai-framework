from __future__ import annotations

"""Admit Ouija from opened Spectral packs only when its exact net value is positive."""

from games.balatro.build.ouija_expectation import OuijaExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


OUIJA = "Ouija"


def install_ouija_pack_expectation_policy() -> None:
    if getattr(BalatroPackPolicy, "_ouija_pack_expectation_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.ouija_expectation_evaluator = OuijaExpectationEvaluator()

    def score_consumable(self, state, action, choice):
        if choice.kind != "SPECTRAL" or choice.label != OUIJA:
            return original_score_consumable(self, state, action, choice)

        expectation = self.ouija_expectation_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(action, -1.0, expectation.rationale)
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Ouija deferred: public rank/hand-size expectation is incomplete",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Ouija does not beat opened-pack Skip=0 after permanent hand-size cost",
                    *expectation.rationale,
                ),
            )
        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                "Ouija uses exact uniform rank expectation minus public future hand-size opportunity cost",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.DEFERRED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.DEFERRED_SPECTRALS) - {OUIJA}
    )
    BalatroPackPolicy._ouija_pack_expectation_installed = True
