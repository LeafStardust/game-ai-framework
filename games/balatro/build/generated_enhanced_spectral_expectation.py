from __future__ import annotations

"""Analytic public-state expectation for Familiar, Grim, and Incantation.

These three Spectrals all perform the same structural operation:

* destroy one uniformly random visible hand card;
* create a fixed number of random Enhanced playing cards from a finite public pool.

The generated rank/suit/enhancement outcome space is explicit in Balatro's mechanic
and in ``spectrals.py``. Stone is excluded because the generated cards retain a real
rank. No Balatro RNG sample or seed is needed: expectation is linear, so the random
destruction branch and generated-card outcomes can be averaged independently even
when the live RNG streams are correlated.

Value deliberately reuses the existing B6 public deck-composition semantics used by
Hanged Man, Immolate, and Cryptid. Generated cards are measured relative to the
current owned-deck average rather than assigned a fixed Spectral/category score.
"""

from dataclasses import dataclass

from games.balatro.card import BalatroCard
from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator
from games.balatro.spectrals import FACE_RANKS, GENERATED_ENHANCEMENTS, NUMBERED_RANKS, SUITS


@dataclass(frozen=True)
class GeneratedEnhancedSpectralSpec:
    name: str
    ranks: tuple[str, ...]
    generated_count: int


SPECS = {
    "Familiar": GeneratedEnhancedSpectralSpec(
        name="Familiar",
        ranks=tuple(FACE_RANKS),
        generated_count=3,
    ),
    "Grim": GeneratedEnhancedSpectralSpec(
        name="Grim",
        ranks=("A",),
        generated_count=2,
    ),
    "Incantation": GeneratedEnhancedSpectralSpec(
        name="Incantation",
        ranks=tuple(NUMBERED_RANKS),
        generated_count=4,
    ),
}


@dataclass(frozen=True)
class GeneratedEnhancedSpectralExpectation:
    available: bool
    complete: bool
    name: str
    destruction_branch_count: int
    generated_outcome_count: int
    generated_count: int
    expected_destruction_gain: float
    expected_generated_gain: float
    expected_total_gain: float
    rationale: tuple[str, ...] = ()


class GeneratedEnhancedSpectralExpectationEvaluator:
    """Evaluate Familiar/Grim/Incantation from public hand and owned deck."""

    def __init__(
        self,
        *,
        target_evaluator: ContextualConsumableTargetEvaluator | None = None,
    ) -> None:
        self.target_evaluator = target_evaluator or ContextualConsumableTargetEvaluator()

    def evaluate(self, state, name: str) -> GeneratedEnhancedSpectralExpectation:
        spec = SPECS.get(str(name))
        if spec is None:
            return GeneratedEnhancedSpectralExpectation(
                available=False,
                complete=False,
                name=str(name),
                destruction_branch_count=0,
                generated_outcome_count=0,
                generated_count=0,
                expected_destruction_gain=0.0,
                expected_generated_gain=0.0,
                expected_total_gain=0.0,
                rationale=(f"unsupported generated-card Spectral: {name}",),
            )

        hand = list(getattr(state, "hand", ()) or ())
        if len(hand) <= 1:
            return GeneratedEnhancedSpectralExpectation(
                available=False,
                complete=True,
                name=spec.name,
                destruction_branch_count=0,
                generated_outcome_count=0,
                generated_count=spec.generated_count,
                expected_destruction_gain=0.0,
                expected_generated_gain=0.0,
                expected_total_gain=0.0,
                rationale=(f"{spec.name} requires more than one public hand card",),
            )

        owned = self.target_evaluator._owned_deck_for_thinning(state)
        if owned is None or not owned[0]:
            return GeneratedEnhancedSpectralExpectation(
                available=True,
                complete=False,
                name=spec.name,
                destruction_branch_count=0,
                generated_outcome_count=0,
                generated_count=spec.generated_count,
                expected_destruction_gain=0.0,
                expected_generated_gain=0.0,
                expected_total_gain=0.0,
                rationale=(
                    f"{spec.name} expectation requires a complete public owned-deck composition",
                ),
            )

        owned_cards, source = owned
        profile_state = state.copy()
        profile_state.deck = list(owned_cards)
        profile = self.target_evaluator.profiler.profile(profile_state)

        try:
            owned_intrinsic = [
                self.target_evaluator._card_intrinsic_value(card)
                for card in owned_cards
            ]
            owned_contextual = [
                self.target_evaluator._card_build_value(profile_state, card, profile)
                for card in owned_cards
            ]
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return self._incomplete(spec, "owned-deck B6 valuation failed closed")

        average_intrinsic = sum(owned_intrinsic) / len(owned_intrinsic)
        average_contextual = sum(owned_contextual) / len(owned_contextual)

        destruction_gains: list[float] = []
        try:
            for card in hand:
                intrinsic_delta = average_intrinsic - self.target_evaluator._card_intrinsic_value(card)
                contextual_delta = average_contextual - self.target_evaluator._card_build_value(
                    profile_state,
                    card,
                    profile,
                )
                destruction_gains.append(
                    intrinsic_delta
                    + contextual_delta
                    + self.target_evaluator.deck_thinning_value
                )
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return self._incomplete(spec, "random destruction branch valuation failed closed")

        generated_gains: list[float] = []
        try:
            for rank in spec.ranks:
                for suit in SUITS:
                    for enhancement in GENERATED_ENHANCEMENTS:
                        card = BalatroCard(rank, suit, enhancement=enhancement)
                        intrinsic_delta = (
                            self.target_evaluator._card_intrinsic_value(card)
                            - average_intrinsic
                        )
                        contextual_delta = (
                            self.target_evaluator._card_build_value(
                                profile_state,
                                card,
                                profile,
                            )
                            - average_contextual
                        )
                        generated_gains.append(intrinsic_delta + contextual_delta)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return self._incomplete(spec, "generated Enhanced-card branch valuation failed closed")

        if not destruction_gains or not generated_gains:
            return self._incomplete(spec, "finite public outcome space unexpectedly empty")

        expected_destruction = sum(destruction_gains) / len(destruction_gains)
        expected_generated_per_card = sum(generated_gains) / len(generated_gains)
        expected_generated = spec.generated_count * expected_generated_per_card
        total = expected_destruction + expected_generated

        return GeneratedEnhancedSpectralExpectation(
            available=True,
            complete=True,
            name=spec.name,
            destruction_branch_count=len(destruction_gains),
            generated_outcome_count=len(generated_gains),
            generated_count=spec.generated_count,
            expected_destruction_gain=expected_destruction,
            expected_generated_gain=expected_generated,
            expected_total_gain=total,
            rationale=(
                f"owned deck source={source}",
                f"owned deck size={len(owned_cards)}",
                f"uniform visible destruction branches={len(destruction_gains)}",
                f"finite generated card outcomes per card={len(generated_gains)}",
                f"generated cards={spec.generated_count}",
                f"expected random-destruction B6 gain={expected_destruction:.3f}",
                f"expected generated-card B6 gain={expected_generated:.3f}",
                f"expected {spec.name} total gain={total:.3f}",
                "Stone is excluded from ranked generated Enhanced cards",
                "no Balatro RNG sample, seed, future draw order, or hidden pack content read",
            ),
        )

    @staticmethod
    def _incomplete(
        spec: GeneratedEnhancedSpectralSpec,
        reason: str,
    ) -> GeneratedEnhancedSpectralExpectation:
        return GeneratedEnhancedSpectralExpectation(
            available=True,
            complete=False,
            name=spec.name,
            destruction_branch_count=0,
            generated_outcome_count=0,
            generated_count=spec.generated_count,
            expected_destruction_gain=0.0,
            expected_generated_gain=0.0,
            expected_total_gain=0.0,
            rationale=(reason,),
        )
