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


def _token(value: object) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _showman_owned(state) -> bool:
    return any(
        _token(
            getattr(joker, "name", None)
            or getattr(joker, "label", None)
            or type(joker).__name__
        )
        in {"showman", "showmanjoker"}
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _held_consumable_names(state) -> frozenset[str]:
    return frozenset(
        str(getattr(consumable, "name", "") or "")
        for consumable in tuple(getattr(state, "consumables", ()) or ())
        if str(getattr(consumable, "name", "") or "")
    )


class HighPriestessExpectationEvaluator:
    """Value High Priestess from its real public Planet generation pool.

    The card creates up to two random Planet cards. The exact outcomes are hidden,
    but the eligible pool is public and finite: the base nine plus any secret
    Planets unlocked by public hand-play history. Without Showman, Balatro's normal
    duplicate-prevention rule excludes consumables already held by the player and
    also prevents the two generated cards from duplicating one another. Showman
    permits duplicates.

    Every remaining public branch is valued with the same consumable item estimator
    used by ordinary Planet choices. No RNG sample, seed, future draw, or hidden pack
    content is read.
    """

    def __init__(self, *, item_estimator=None) -> None:
        self.item_estimator = item_estimator or DefaultShopItemValueEstimator()

    def evaluate(self, state) -> HighPriestessExpectation:
        capacity = max(0, int(getattr(state, "consumable_slots", 0) or 0))
        occupied = len(tuple(getattr(state, "consumables", ()) or ()))
        free_slots = max(0, capacity - occupied)
        if free_slots <= 0:
            return HighPriestessExpectation(
                available=False,
                complete=True,
                generated_count=0,
                expected_total_gain=0.0,
                rationale=(f"no free consumable slots ({occupied}/{capacity})",),
            )

        showman = _showman_owned(state)
        held_names = _held_consumable_names(state)
        eligible_names = tuple(eligible_planet_names(state))

        pool: list[str] = []
        excluded: list[str] = []
        for name in eligible_names:
            planet = create_planet(name)
            label = str(getattr(planet, "name", name))
            if not showman and label in held_names:
                excluded.append(label)
                continue
            pool.append(name)

        if not pool:
            return HighPriestessExpectation(
                available=True,
                complete=True,
                generated_count=0,
                expected_total_gain=0.0,
                rationale=(
                    "public Planet generation pool is empty after duplicate exclusions",
                    f"Showman={'owned' if showman else 'absent'}",
                    *(
                        ("held duplicate exclusions=" + ", ".join(sorted(excluded)),)
                        if excluded
                        else ()
                    ),
                ),
            )

        generated_count = min(
            2,
            free_slots,
            2 if showman else len(pool),
        )

        outcomes: list[HighPriestessPlanetOutcome] = []
        notes: list[str] = []
        try:
            for name in pool:
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

        # Without Showman the second generation is sampled without replacement.
        # For a uniformly weighted finite pool, the expected sum of two draws
        # without replacement is still two times the initial pool mean. With
        # Showman it is sampling with replacement, which has the same expectation.
        mean_value = sum(outcome.held_value for outcome in outcomes) / len(outcomes)
        expected_total = mean_value * generated_count
        return HighPriestessExpectation(
            available=True,
            complete=True,
            generated_count=generated_count,
            expected_total_gain=expected_total,
            outcomes=tuple(outcomes),
            rationale=(
                "uniform expectation over the public generatable Planet pool",
                f"eligible Planet outcomes={len(outcomes)}",
                f"Showman={'owned; duplicates allowed' if showman else 'absent; held/generated duplicates excluded'}",
                *(
                    ("held duplicate exclusions=" + ", ".join(sorted(excluded)),)
                    if excluded
                    else ()
                ),
                f"free consumable slots={free_slots}; generated cards={generated_count}",
                f"mean generated Planet value={mean_value:.3f}",
                f"expected total generated value={expected_total:.3f}",
                *notes,
            ),
        )
