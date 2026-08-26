from __future__ import annotations

"""Admit Ectoplasm from opened Spectral packs only when its exact net value is positive."""

from games.balatro.build.ectoplasm_expectation import EctoplasmExpectationEvaluator
from games.balatro.ectoplasm_dispatch_postcondition import install_ectoplasm_dispatch_postcondition
from games.balatro.ectoplasm_live_state_policy import install_ectoplasm_live_state_policy
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


ECTOPLASM = "Ectoplasm"


def install_ectoplasm_pack_expectation_policy() -> None:
    install_ectoplasm_live_state_policy()
    install_ectoplasm_dispatch_postcondition()
    if getattr(BalatroPackPolicy, "_ectoplasm_pack_expectation_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.ectoplasm_expectation_evaluator = EctoplasmExpectationEvaluator()

    def score_consumable(self, state, action, choice):
        if choice.kind != "SPECTRAL" or choice.label != ECTOPLASM:
            return original_score_consumable(self, state, action, choice)

        expectation = self.ectoplasm_expectation_evaluator.evaluate(state)
        if not expectation.available:
            return PackActionScore(action, -1.0, expectation.rationale)
        if not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Ectoplasm deferred: public Negative-slot/hand-size tradeoff is incomplete",
                    *expectation.rationale,
                ),
            )
        if expectation.expected_total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Ectoplasm does not beat opened-pack Skip=0 after escalating hand-size cost",
                    *expectation.rationale,
                ),
            )
        return PackActionScore(
            action,
            float(expectation.expected_total_gain),
            (
                "Ectoplasm uses marginal public future-Joker capacity minus literal hand-size opportunity cost",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS) | {ECTOPLASM}
    )
    BalatroPackPolicy.DEFERRED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.DEFERRED_SPECTRALS) - {ECTOPLASM}
    )
    BalatroPackPolicy._ectoplasm_pack_expectation_installed = True
