from __future__ import annotations

from dataclasses import dataclass

from games.balatro.build.playing_card_synergy import (
    ContextualPlayingCardSynergyEvaluator,
)
from games.balatro.build.profile import BalatroBuildProfiler


@dataclass(frozen=True)
class AuraTargetExpectation:
    """Analytic public-state value for one Aura target recommendation."""

    available: bool
    complete: bool
    target_index: int | None
    expected_intrinsic_gain: float
    expected_contextual_gain: float
    expected_total_gain: float
    rationale: tuple[str, ...] = ()


class AuraExpectationEvaluator:
    """Choose an editionless hand target by analytically valuing Aura outcomes.

    Aura uses Balatro's vanilla conditional edition weights: Foil 50%,
    Holographic 35%, and Polychrome 15%. This evaluator enumerates those public
    semantic outcomes instead of sampling RNG. Existing editions are excluded so
    autonomous play never recommends an impossible edition overwrite.
    """

    EDITION_OUTCOMES = (
        ("Foil", 0.50),
        ("Holographic", 0.35),
        ("Polychrome", 0.15),
    )
    EDITION_INTRINSIC_VALUE = {
        "Foil": 0.80,
        "Holographic": 1.50,
        "Polychrome": 2.50,
    }

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        card_evaluator: ContextualPlayingCardSynergyEvaluator | None = None,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.card_evaluator = card_evaluator or ContextualPlayingCardSynergyEvaluator(
            profiler=self.profiler
        )

    def evaluate(self, state) -> AuraTargetExpectation:
        hand = list(getattr(state, "hand", ()))
        eligible = tuple(
            index
            for index, card in enumerate(hand)
            if getattr(card, "edition", None) in (None, "")
        )
        if not eligible:
            return AuraTargetExpectation(
                available=False,
                complete=True,
                target_index=None,
                expected_intrinsic_gain=0.0,
                expected_contextual_gain=0.0,
                expected_total_gain=0.0,
                rationale=("Aura has no editionless public hand target",),
            )

        profile = self.profiler.profile(state)
        ranked: list[tuple[float, int, float, float]] = []
        for index in eligible:
            card = hand[index]
            try:
                before_contextual = float(
                    self.card_evaluator.evaluate(
                        state,
                        rank=card.rank,
                        suit=card.suit,
                        enhancement=card.enhancement,
                        seal=card.seal,
                        edition=card.edition,
                        profile=profile,
                    ).total_gain
                )
                intrinsic_gain = 0.0
                contextual_gain = 0.0
                for edition, probability in self.EDITION_OUTCOMES:
                    intrinsic_gain += (
                        probability * self.EDITION_INTRINSIC_VALUE[edition]
                    )
                    after_contextual = float(
                        self.card_evaluator.evaluate(
                            state,
                            rank=card.rank,
                            suit=card.suit,
                            enhancement=card.enhancement,
                            seal=card.seal,
                            edition=edition,
                            profile=profile,
                        ).total_gain
                    )
                    contextual_gain += probability * (
                        after_contextual - before_contextual
                    )
            except (
                AttributeError,
                IndexError,
                KeyError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ):
                return AuraTargetExpectation(
                    available=True,
                    complete=False,
                    target_index=None,
                    expected_intrinsic_gain=0.0,
                    expected_contextual_gain=0.0,
                    expected_total_gain=0.0,
                    rationale=(
                        "Aura expectation failed closed on an incomplete edition branch",
                    ),
                )

            total_gain = intrinsic_gain + contextual_gain
            ranked.append((total_gain, index, intrinsic_gain, contextual_gain))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        total_gain, index, intrinsic_gain, contextual_gain = ranked[0]
        return AuraTargetExpectation(
            available=True,
            complete=True,
            target_index=index,
            expected_intrinsic_gain=intrinsic_gain,
            expected_contextual_gain=contextual_gain,
            expected_total_gain=total_gain,
            rationale=(
                f"editionless Aura targets={len(eligible)}",
                "Aura conditional edition weights=Foil 0.50/Holographic 0.35/Polychrome 0.15",
                f"selected target index={index}",
                f"expected intrinsic edition gain={intrinsic_gain:.3f}",
                f"expected B6 contextual edition gain={contextual_gain:.3f}",
                f"expected Aura target gain={total_gain:.3f}",
            ),
        )
