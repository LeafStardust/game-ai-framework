from __future__ import annotations

"""Replace synthetic Soul pack value with modeled Legendary build expectation."""

from games.balatro.build.soul_expectation import SoulExpectationEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


def install_soul_pack_expectation_policy() -> None:
    if getattr(BalatroPackPolicy, "_soul_expectation_installed", False):
        return

    original_init = BalatroPackPolicy.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.soul_evaluator = SoulExpectationEvaluator(
            build_value=getattr(self.item_estimator, "joker_build_value", None)
        )

    def score_soul(self, state, action, target):
        joker_slots = max(0, int(getattr(state, "joker_slots", 5) or 5))
        owned_jokers = len(tuple(getattr(state, "jokers", ()) or ()))
        if owned_jokers >= joker_slots or not target.can_use(
            ConsumableContext(state=state)
        ):
            return PackActionScore(
                action,
                -1.0,
                (
                    "The Soul unavailable: no free Joker slot "
                    f"({owned_jokers}/{joker_slots})",
                ),
            )

        expectation = self.soul_evaluator.evaluate(state)
        if not expectation.available or not expectation.complete:
            return PackActionScore(
                action,
                -1.0,
                (
                    "The Soul deferred: modeled Legendary expectation incomplete",
                    *expectation.rationale,
                ),
            )

        return PackActionScore(
            action,
            float(expectation.expected_build_gain),
            (
                "The Soul uses current-build expectation over modeled Legendary outcomes",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_soul = score_soul
    BalatroPackPolicy._soul_expectation_installed = True
