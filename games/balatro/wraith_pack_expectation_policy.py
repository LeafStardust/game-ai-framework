from __future__ import annotations

"""Opened-pack Wraith policy from the public eligible Rare-Joker catalogue."""

from games.balatro.build.wraith_expectation import WraithExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


WRAITH = "Wraith"


def install_wraith_pack_expectation_policy() -> None:
    if getattr(BalatroPackPolicy, "_wraith_pack_expectation_policy_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.wraith_expectation_evaluator = WraithExpectationEvaluator(
            joker_factory=self.joker_factory,
            joker_value=getattr(self.item_estimator, "joker_build_value", None),
        )

    def score_consumable(self, state, action, choice):
        if choice.kind != "SPECTRAL" or choice.label != WRAITH:
            return original_score_consumable(self, state, action, choice)

        expectation = self.wraith_expectation_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Wraith unavailable in current public state", *expectation.rationale),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                ("Wraith deferred: public outcome expectation incomplete", *expectation.rationale),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                ("Wraith does not beat the opened-pack skip baseline", *expectation.rationale),
            )

        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                "Wraith uses public Rare-Joker expectation minus exact cash-reset resource cost",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS) | {WRAITH}
    )
    BalatroPackPolicy.DEFERRED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.DEFERRED_SPECTRALS) - {WRAITH}
    )
    BalatroPackPolicy._wraith_pack_expectation_policy_installed = True
