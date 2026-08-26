from __future__ import annotations

"""Opened-pack Judgement policy from the live eligible Joker catalogue."""

from games.balatro.build.judgement_expectation import JudgementExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


JUDGEMENT = "Judgement"


def install_judgement_pack_expectation_policy() -> None:
    if getattr(BalatroPackPolicy, "_judgement_pack_expectation_policy_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.judgement_expectation_evaluator = JudgementExpectationEvaluator(
            joker_factory=self.joker_factory,
            joker_value=getattr(self.item_estimator, "joker_build_value", None),
        )

    def score_consumable(self, state, action, choice):
        if choice.kind != "TAROT" or choice.label != JUDGEMENT:
            return original_score_consumable(self, state, action, choice)

        expectation = self.judgement_expectation_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(
                action,
                -1.0,
                ("Judgement unavailable in current public state", *expectation.rationale),
            )
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                ("Judgement deferred: public Joker expectation incomplete", *expectation.rationale),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                ("Judgement does not beat the opened-pack skip baseline", *expectation.rationale),
            )

        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                "Judgement uses analytic public eligible-Joker expectation",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS) | {JUDGEMENT}
    )
    BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS) - {JUDGEMENT}
    )
    BalatroPackPolicy._judgement_pack_expectation_policy_installed = True
