from __future__ import annotations

"""Analytic public-state expectation for Immolate.

Immolate destroys five uniformly sampled cards from the current visible hand and
awards a deterministic $20.  The random branch is therefore finite and fully
observable: enumerate every five-card subset rather than sampling Balatro RNG.

Card-removal value deliberately reuses the existing Hanged-Man B6 semantics from
``ContextualConsumableTargetEvaluator``.  The money term uses the same legacy
policy-facing deterministic-money curve already used by Hermit/Temperance; this
module does not create a competing dollar/value scale.
"""

from dataclasses import dataclass
from itertools import combinations

from games.balatro.build.consumable_targeting import (
    ContextualConsumableTargetEvaluator,
)


IMMOLATE_MONEY_GAIN = 20


@dataclass(frozen=True)
class ImmolateExpectation:
    available: bool
    complete: bool
    branch_count: int
    expected_removal_gain: float
    money_utility: float
    expected_total_gain: float
    rationale: tuple[str, ...] = ()


class ImmolateExpectationEvaluator:
    """Enumerate every public five-card Immolate destruction branch."""

    def __init__(
        self,
        *,
        target_evaluator: ContextualConsumableTargetEvaluator | None = None,
    ) -> None:
        self.target_evaluator = (
            target_evaluator or ContextualConsumableTargetEvaluator()
        )

    def evaluate(self, state) -> ImmolateExpectation:
        hand = list(getattr(state, "hand", ()))
        if len(hand) < 5:
            return ImmolateExpectation(
                available=False,
                complete=True,
                branch_count=0,
                expected_removal_gain=0.0,
                money_utility=0.0,
                expected_total_gain=0.0,
                rationale=("Immolate requires at least five public hand cards",),
            )

        owned = self.target_evaluator._owned_deck_for_thinning(state)
        if owned is None or not owned[0]:
            return ImmolateExpectation(
                available=True,
                complete=False,
                branch_count=0,
                expected_removal_gain=0.0,
                money_utility=0.0,
                expected_total_gain=0.0,
                rationale=(
                    "Immolate expectation requires a complete public owned-deck composition",
                ),
            )

        owned_cards, source = owned
        profile_state = state.copy()
        profile_state.deck = list(owned_cards)
        profile = self.target_evaluator.profiler.profile(profile_state)

        try:
            intrinsic_values = [
                self.target_evaluator._card_intrinsic_value(card)
                for card in owned_cards
            ]
            contextual_values = [
                self.target_evaluator._card_build_value(profile_state, card, profile)
                for card in owned_cards
            ]
        except (
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            ZeroDivisionError,
        ):
            return ImmolateExpectation(
                available=True,
                complete=False,
                branch_count=0,
                expected_removal_gain=0.0,
                money_utility=0.0,
                expected_total_gain=0.0,
                rationale=("Immolate B6 owned-deck valuation failed closed",),
            )

        average_intrinsic = sum(intrinsic_values) / len(intrinsic_values)
        average_contextual = sum(contextual_values) / len(contextual_values)

        branch_gains: list[float] = []
        for indices in combinations(range(len(hand)), 5):
            cards = [hand[index] for index in indices]
            try:
                intrinsic_delta = sum(
                    average_intrinsic
                    - self.target_evaluator._card_intrinsic_value(card)
                    for card in cards
                )
                contextual_delta = sum(
                    average_contextual
                    - self.target_evaluator._card_build_value(
                        profile_state,
                        card,
                        profile,
                    )
                    for card in cards
                )
            except (
                AttributeError,
                IndexError,
                KeyError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ):
                return ImmolateExpectation(
                    available=True,
                    complete=False,
                    branch_count=len(branch_gains),
                    expected_removal_gain=0.0,
                    money_utility=0.0,
                    expected_total_gain=0.0,
                    rationale=(
                        "Immolate expectation failed closed on an incomplete five-card branch",
                    ),
                )

            thinning_gain = self.target_evaluator.deck_thinning_value * len(cards)
            branch_gains.append(
                intrinsic_delta + contextual_delta + thinning_gain
            )

        if not branch_gains:
            return ImmolateExpectation(
                available=True,
                complete=False,
                branch_count=0,
                expected_removal_gain=0.0,
                money_utility=0.0,
                expected_total_gain=0.0,
                rationale=("Immolate produced no public destruction branches",),
            )

        expected_removal = sum(branch_gains) / len(branch_gains)
        # Existing DefaultShopItemValueEstimator deterministic-money scale:
        # 2.2 + min(5.0, gain * 0.35).  Immolate's gain is always exactly $20.
        money_utility = 2.2 + min(5.0, IMMOLATE_MONEY_GAIN * 0.35)
        total = expected_removal + money_utility

        return ImmolateExpectation(
            available=True,
            complete=True,
            branch_count=len(branch_gains),
            expected_removal_gain=expected_removal,
            money_utility=money_utility,
            expected_total_gain=total,
            rationale=(
                f"owned deck source={source}",
                f"owned deck size={len(owned_cards)}",
                f"uniform public five-card branches={len(branch_gains)}",
                f"expected B6 removal gain={expected_removal:.3f}",
                f"deterministic money gain=${IMMOLATE_MONEY_GAIN}",
                f"existing deterministic-money utility={money_utility:.3f}",
                f"expected Immolate total gain={total:.3f}",
                "no Balatro RNG sample or seed read",
            ),
        )
