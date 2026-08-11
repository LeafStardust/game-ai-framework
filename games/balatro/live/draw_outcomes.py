from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import comb
import random

from games.balatro.card import BalatroCard
from games.balatro.live.draw_model import PublicCardSignature, PublicDeckComposition


@dataclass(frozen=True)
class PublicDrawOutcome:
    """One unordered public draw result.

    Cards are signatures rather than live objects so no serialized draw order or
    live identity can leak into planner state.
    """

    cards: tuple[PublicCardSignature, ...]
    probability: float


@dataclass(frozen=True)
class PublicDrawDistribution:
    outcomes: tuple[PublicDrawOutcome, ...]
    draws: int
    population_size: int
    combination_count: int
    exact: bool
    sample_count: int = 0

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise ValueError("public draw distribution requires at least one outcome")
        probability = sum(outcome.probability for outcome in self.outcomes)
        if abs(probability - 1.0) > 1e-9:
            raise ValueError(
                "public draw outcome probabilities must sum to 1.0, got "
                f"{probability}"
            )


class PublicDrawOutcomeModel:
    """Produce draw branches from unordered public deck composition.

    Small outcome spaces are enumerated exactly. Large spaces are represented by
    deterministic uniform samples from the public multiset; the fixed sampling is
    for reproducible planning only and never consults Balatro's hidden RNG/order.
    """

    def __init__(
        self,
        *,
        exact_combination_limit: int = 25_000,
        sample_count: int = 256,
        seed: int = 0,
    ):
        if exact_combination_limit < 1:
            raise ValueError("exact_combination_limit must be positive")
        if sample_count < 1:
            raise ValueError("sample_count must be positive")
        self.exact_combination_limit = int(exact_combination_limit)
        self.sample_count = int(sample_count)
        self.seed = int(seed)

    def distribution(
        self,
        composition: PublicDeckComposition,
        draws: int,
    ) -> PublicDrawDistribution:
        total = composition.total_cards
        draws = max(0, min(int(draws), total))
        combinations = comb(total, draws) if total >= draws else 0

        if draws == 0:
            return PublicDrawDistribution(
                outcomes=(PublicDrawOutcome((), 1.0),),
                draws=0,
                population_size=total,
                combination_count=1,
                exact=True,
            )

        if combinations <= self.exact_combination_limit:
            outcomes = self._exact(composition, draws, combinations)
            return PublicDrawDistribution(
                outcomes=outcomes,
                draws=draws,
                population_size=total,
                combination_count=combinations,
                exact=True,
            )

        outcomes = self._sampled(composition, draws)
        return PublicDrawDistribution(
            outcomes=outcomes,
            draws=draws,
            population_size=total,
            combination_count=combinations,
            exact=False,
            sample_count=self.sample_count,
        )

    def remaining_cards(
        self,
        composition: PublicDeckComposition,
        outcome: PublicDrawOutcome,
    ) -> list[BalatroCard]:
        counts = Counter(dict(composition.items()))
        for signature in outcome.cards:
            counts[signature] -= 1
            if counts[signature] < 0:
                raise ValueError("draw outcome contains a card absent from composition")

        result: list[BalatroCard] = []
        for signature, count in sorted(
            counts.items(),
            key=lambda item: item[0].sort_key(),
        ):
            for _ in range(count):
                result.append(self.card_from_signature(signature))
        return result

    @staticmethod
    def card_from_signature(signature: PublicCardSignature) -> BalatroCard:
        return BalatroCard(
            signature.rank,
            signature.suit,
            enhancement=signature.enhancement,
            edition=signature.edition,
            seal=signature.seal,
        )

    def _exact(
        self,
        composition: PublicDeckComposition,
        draws: int,
        denominator: int,
    ) -> tuple[PublicDrawOutcome, ...]:
        items = composition.items()
        results: list[PublicDrawOutcome] = []

        def visit(
            index: int,
            remaining: int,
            selected: list[PublicCardSignature],
            ways: int,
        ) -> None:
            if remaining == 0:
                results.append(
                    PublicDrawOutcome(
                        cards=tuple(selected),
                        probability=ways / denominator,
                    )
                )
                return
            if index >= len(items):
                return

            remaining_population = sum(count for _, count in items[index:])
            if remaining > remaining_population:
                return

            signature, available = items[index]
            maximum = min(available, remaining)
            for amount in range(maximum + 1):
                selected.extend([signature] * amount)
                visit(
                    index + 1,
                    remaining - amount,
                    selected,
                    ways * comb(available, amount),
                )
                if amount:
                    del selected[-amount:]

        visit(0, draws, [], 1)
        return tuple(results)

    def _sampled(
        self,
        composition: PublicDeckComposition,
        draws: int,
    ) -> tuple[PublicDrawOutcome, ...]:
        population: list[PublicCardSignature] = []
        for signature, count in composition.items():
            population.extend([signature] * count)

        rng = random.Random(self._stable_seed(composition, draws))
        counts: Counter[tuple[PublicCardSignature, ...]] = Counter()
        indices = list(range(len(population)))
        for _ in range(self.sample_count):
            picked = rng.sample(indices, draws)
            cards = tuple(
                sorted(
                    (population[index] for index in picked),
                    key=lambda signature: signature.sort_key(),
                )
            )
            counts[cards] += 1

        return tuple(
            PublicDrawOutcome(
                cards=cards,
                probability=count / self.sample_count,
            )
            for cards, count in sorted(
                counts.items(),
                key=lambda item: tuple(signature.sort_key() for signature in item[0]),
            )
        )

    def _stable_seed(
        self,
        composition: PublicDeckComposition,
        draws: int,
    ) -> int:
        material = [f"seed={self.seed}", f"draws={draws}"]
        for signature, count in composition.items():
            material.append(f"{signature.sort_key()}={count}")
        digest = sha256("|".join(material).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big", signed=False)
