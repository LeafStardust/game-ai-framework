from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import BUY_CONSUMABLE, BalatroAction
from games.balatro.planets import create_planet, eligible_planet_names
from games.balatro.shop_policy import DefaultShopItemValueEstimator


@dataclass(frozen=True)
class HighPriestessPlanetOutcome:
    planet_name: str
    held_value: float


@dataclass(frozen=True)
class HighPriestessExpectation:
    available: bool
    complete: bool
    generated_count: int
    expected_total_gain: float
    outcomes: tuple[HighPriestessPlanetOutcome, ...] = ()
    rationale: tuple[str, ...] = ()


class HighPriestessExpectationEvaluator:
    """Value High Priestess from its public eligible Planet pool.

    The card creates up to two random Planet cards.  The exact outcomes are hidden,
    but the eligible pool is public and finite: the base nine plus any secret
    Planets unlocked by public hand-play history.  Each branch is valued with the
    same consumable item estimator used by ordinary Planet choices, then multiplied
    by the number of currently free consumable slots (capped at two).

    No RNG sample, seed, future draw, or hidden pack content is read.
    """

    def __init__(self, *, item_estimator=None) -> None:
        self.item_estimator = item_estimator or DefaultShopItemValueEstimator()

    def evaluate(self, state) -> HighPriestessExpectation:
        capacity = max(0, int(getattr(state, "consumable_slots", 0) or 0))
        occupied = len(tuple(getattr(state, "consumables", ()) or ()))
        free_slots = max(0, capacity - occupied)
        generated_count = min(2, free_slots)
        if generated_count <= 0:
            return HighPriestessExpectation(
                available=False,
                complete=True,
                generated_count=0,
                expected_total_gain=0.0,
                rationale=(f"no free consumable slots ({occupied}/{capacity})",),
            )

        names = tuple(eligible_planet_names(state))
        if not names:
            return HighPriestessExpectation(
                available=True,
                complete=False,
                generated_count=generated_count,
                expected_total_gain=0.0,
                rationale=("eligible Planet pool is empty",),
            )

        outcomes: list[HighPriestessPlanetOutcome] = []
        notes: list[str] = []
        try:
            for name in names:
                planet = create_planet(name)
                value, _ = self.item_estimator.estimate(
                    state,
                    BalatroAction(BUY_CONSUMABLE, target=planet),
                )
                held_value = float(value)
                outcomes.append(
                    HighPriestessPlanetOutcome(
                        planet_name=str(getattr(planet, "name", name)),
                        held_value=held_value,
                    )
                )
                notes.append(
                    f"{getattr(planet, 'name', name)} held value={held_value:.3f}"
                )
        except (AttributeError, TypeError, ValueError) as exc:
            return HighPriestessExpectation(
                available=True,
                complete=False,
                generated_count=generated_count,
                expected_total_gain=0.0,
                outcomes=tuple(outcomes),
                rationale=(
                    "Planet branch evaluation incomplete",
                    f"{type(exc).__name__}: {exc}",
                    *notes,
                ),
            )

        if not outcomes:
            return HighPriestessExpectation(
                available=True,
                complete=False,
                generated_count=generated_count,
                expected_total_gain=0.0,
                rationale=("no modeled eligible Planet outcomes",),
            )

        mean_value = sum(outcome.held_value for outcome in outcomes) / len(outcomes)
        expected_total = mean_value * generated_count
        return HighPriestessExpectation(
            available=True,
            complete=True,
            generated_count=generated_count,
            expected_total_gain=expected_total,
            outcomes=tuple(outcomes),
            rationale=(
                "uniform expectation over the public eligible Planet pool",
                f"eligible Planet outcomes={len(outcomes)}",
                f"free consumable slots={free_slots}; generated cards={generated_count}",
                f"mean generated Planet value={mean_value:.3f}",
                f"expected total generated value={expected_total:.3f}",
                *notes,
            ),
        )
