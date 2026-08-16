from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import comb
from typing import Callable, Iterable


@dataclass(frozen=True)
class PublicCardSignature:
    """Public card attributes that are safe to use for draw probabilities.

    Identity and list position are deliberately excluded. The live save may retain
    the serialized order of Balatro's draw pile, but a normal player cannot know
    that order. Planner code must operate on these unordered signatures instead.

    ``debuffed`` is public current-Blind state owned by each playing card. Balatro
    applies the active Blind's debuff to every ``G.playing_cards`` object, including
    cards still in the draw pile, so preserving this flag does not expose hidden
    draw order. ``permanent_bonus`` is likewise public card-owned state and must
    survive hypothetical redraws (for example after Hiker has upgraded a card).
    """

    rank: str
    suit: str
    enhancement: str | None = None
    edition: str | None = None
    seal: str | None = None
    debuffed: bool = False
    permanent_bonus: int = 0

    @classmethod
    def from_card(cls, card) -> "PublicCardSignature":
        return cls(
            rank=str(getattr(card, "rank", "")),
            suit=str(getattr(card, "suit", "")),
            enhancement=getattr(card, "enhancement", None),
            edition=getattr(card, "edition", None),
            seal=getattr(card, "seal", None),
            debuffed=bool(getattr(card, "debuffed", False)),
            permanent_bonus=int(getattr(card, "permanent_bonus", 0) or 0),
        )

    def sort_key(self) -> tuple[str, ...]:
        return (
            self.rank,
            self.suit,
            self.enhancement or "",
            self.edition or "",
            self.seal or "",
            "1" if self.debuffed else "0",
            str(self.permanent_bonus),
        )


@dataclass(frozen=True)
class DrawCountOutcome:
    matches: int
    probability: float


class PublicDeckComposition:
    """Unordered public composition of the current remaining draw pile."""

    def __init__(self, counts: Counter[PublicCardSignature] | dict[PublicCardSignature, int]):
        normalized = Counter()
        for signature, count in counts.items():
            value = int(count)
            if value < 0:
                raise ValueError("public deck card counts cannot be negative")
            if value:
                normalized[signature] += value
        self._counts = normalized

    @classmethod
    def from_cards(cls, cards: Iterable) -> "PublicDeckComposition":
        return cls(Counter(PublicCardSignature.from_card(card) for card in cards))

    @classmethod
    def from_state(cls, state) -> "PublicDeckComposition":
        return cls.from_cards(getattr(state, "deck", []))

    @property
    def total_cards(self) -> int:
        return sum(self._counts.values())

    @property
    def unique_signatures(self) -> int:
        return len(self._counts)

    def count(self, signature: PublicCardSignature) -> int:
        return self._counts[signature]

    def items(self) -> tuple[tuple[PublicCardSignature, int], ...]:
        """Return deterministic aggregate output without revealing draw order."""
        return tuple(
            sorted(
                self._counts.items(),
                key=lambda item: item[0].sort_key(),
            )
        )

    def count_matching(
        self,
        predicate: Callable[[PublicCardSignature], bool],
    ) -> int:
        return sum(
            count
            for signature, count in self._counts.items()
            if predicate(signature)
        )

    def probability_exact_matches(
        self,
        matching_cards: int,
        draws: int,
        matches: int,
    ) -> float:
        """Exact hypergeometric P(X = matches) for draws without replacement."""
        total = self.total_cards
        matching_cards = int(matching_cards)
        draws = int(draws)
        matches = int(matches)

        if matching_cards < 0 or matching_cards > total:
            raise ValueError("matching_cards must be within the remaining deck size")
        if draws < 0:
            raise ValueError("draws cannot be negative")
        if matches < 0:
            return 0.0
        if draws > total:
            draws = total
        if matches > draws or matches > matching_cards:
            return 0.0

        nonmatching = total - matching_cards
        nonmatching_draws = draws - matches
        if nonmatching_draws < 0 or nonmatching_draws > nonmatching:
            return 0.0
        if total == 0:
            return 1.0 if draws == 0 and matches == 0 else 0.0

        denominator = comb(total, draws)
        if denominator == 0:
            return 0.0
        return (
            comb(matching_cards, matches)
            * comb(nonmatching, nonmatching_draws)
            / denominator
        )

    def draw_count_distribution(
        self,
        matching_cards: int,
        draws: int,
    ) -> tuple[DrawCountOutcome, ...]:
        total = self.total_cards
        if matching_cards < 0 or matching_cards > total:
            raise ValueError("matching_cards must be within the remaining deck size")
        if draws < 0:
            raise ValueError("draws cannot be negative")
        draws = min(int(draws), total)

        minimum = max(0, draws - (total - matching_cards))
        maximum = min(draws, matching_cards)
        return tuple(
            DrawCountOutcome(
                matches=value,
                probability=self.probability_exact_matches(
                    matching_cards,
                    draws,
                    value,
                ),
            )
            for value in range(minimum, maximum + 1)
        )

    def probability_at_least_matches(
        self,
        matching_cards: int,
        draws: int,
        minimum_matches: int = 1,
    ) -> float:
        if minimum_matches <= 0:
            return 1.0
        return sum(
            outcome.probability
            for outcome in self.draw_count_distribution(matching_cards, draws)
            if outcome.matches >= minimum_matches
        )

    def probability_at_least(
        self,
        predicate: Callable[[PublicCardSignature], bool],
        draws: int,
        minimum_matches: int = 1,
    ) -> float:
        return self.probability_at_least_matches(
            self.count_matching(predicate),
            draws,
            minimum_matches,
        )

    def probability_rank(
        self,
        rank: str,
        draws: int,
        minimum_matches: int = 1,
    ) -> float:
        rank = str(rank)
        return self.probability_at_least(
            lambda signature: signature.rank == rank,
            draws,
            minimum_matches,
        )

    def probability_suit(
        self,
        suit: str,
        draws: int,
        minimum_matches: int = 1,
    ) -> float:
        suit = str(suit)
        return self.probability_at_least(
            lambda signature: signature.suit == suit,
            draws,
            minimum_matches,
        )
