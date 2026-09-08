from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb


@dataclass(frozen=True)
class PlanetOutlook:
    """Public-state estimate of one Planet's repeatable future value."""

    hand_type: str
    observed_plays: int
    total_observed_plays: int
    observed_frequency: float
    structural_feasibility: float
    expected_future_frequency: float
    marginal_level_gain: float
    future_value: float

    @property
    def speculative(self) -> bool:
        return self.observed_plays <= 0 and self.structural_feasibility < 0.01


class PlanetOutlookEvaluator:
    """Estimate Planet value without hidden draws, seed data, or named builds.

    Structural feasibility is computed from the unordered public owned deck. It is
    the approximate chance that a future hand of the current hand size contains at
    least one qualifying subset for the Planet's poker hand. Public hand-play
    history gradually replaces that structural prior as evidence accumulates.
    """

    _RANK_ORDER = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }
    _SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")

    def evaluate(self, state, planet: object) -> PlanetOutlook:
        hand_type = str(getattr(planet, "hand_type", ""))
        counts = getattr(state, "hand_play_counts", {}) or {}
        observed_plays = max(0, int(counts.get(hand_type, 0) or 0))
        total_observed = sum(max(0, int(value or 0)) for value in counts.values())
        observed_frequency = (
            float(observed_plays) / float(total_observed)
            if total_observed > 0
            else 0.0
        )

        structural = self._structural_feasibility(state, hand_type)
        evidence_weight = min(1.0, float(total_observed) / 8.0)
        expected_frequency = (
            evidence_weight * observed_frequency
            + (1.0 - evidence_weight) * structural
        )

        chips = max(0.0, float(getattr(planet, "chips", 0.0) or 0.0))
        mult = max(0.0, float(getattr(planet, "mult", 0.0) or 0.0))
        # Keep the same public score scale historically used by shop Planet value,
        # but apply it to the expected frequency of actually using that hand.
        marginal_level_gain = chips * 0.04 + mult * 0.30
        future_value = marginal_level_gain * expected_frequency

        return PlanetOutlook(
            hand_type=hand_type,
            observed_plays=observed_plays,
            total_observed_plays=total_observed,
            observed_frequency=observed_frequency,
            structural_feasibility=structural,
            expected_future_frequency=expected_frequency,
            marginal_level_gain=marginal_level_gain,
            future_value=future_value,
        )

    def _structural_feasibility(self, state, hand_type: str) -> float:
        cards = self._owned_regular_cards(state)
        n = len(cards)
        if n <= 0:
            return 0.0
        if hand_type == "HIGH_CARD":
            return 1.0

        hand_size = max(1, int(getattr(state, "hand_size", 8) or 8))
        hand_size = min(hand_size, n)
        rules = dict(getattr(state, "hand_rules", {}) or {})
        rank_counts = Counter(str(getattr(card, "rank", "")) for card in cards)

        if hand_type == "PAIR":
            return self._subset_opportunity(
                n,
                hand_size,
                2,
                sum(comb(count, 2) for count in rank_counts.values() if count >= 2),
            )
        if hand_type == "TWO_PAIR":
            qualifying = sum(
                comb(left, 2) * comb(right, 2)
                for (_, left), (_, right) in combinations(rank_counts.items(), 2)
                if left >= 2 and right >= 2
            )
            return self._subset_opportunity(n, hand_size, 4, qualifying)
        if hand_type == "THREE_OF_A_KIND":
            return self._subset_opportunity(
                n,
                hand_size,
                3,
                sum(comb(count, 3) for count in rank_counts.values() if count >= 3),
            )
        if hand_type == "FOUR_OF_A_KIND":
            return self._subset_opportunity(
                n,
                hand_size,
                4,
                sum(comb(count, 4) for count in rank_counts.values() if count >= 4),
            )
        if hand_type == "FIVE_OF_A_KIND":
            return self._subset_opportunity(
                n,
                hand_size,
                5,
                sum(comb(count, 5) for count in rank_counts.values() if count >= 5),
            )
        if hand_type == "FULL_HOUSE":
            qualifying = sum(
                comb(trips, 3) * comb(pair, 2)
                for trip_rank, trips in rank_counts.items()
                for pair_rank, pair in rank_counts.items()
                if trip_rank != pair_rank and trips >= 3 and pair >= 2
            )
            return self._subset_opportunity(n, hand_size, 5, qualifying)
        if hand_type == "STRAIGHT":
            required = max(1, int(rules.get("straight_size", 5) or 5))
            qualifying = self._straight_combo_count(
                rank_counts,
                required=required,
                max_step=2 if rules.get("shortcut") else 1,
            )
            return self._subset_opportunity(n, hand_size, required, qualifying)
        if hand_type == "FLUSH":
            required = max(1, int(rules.get("flush_size", 5) or 5))
            qualifying = sum(
                comb(sum(counts.values()), required)
                for counts in self._effective_suit_rank_counts(cards, rules).values()
                if sum(counts.values()) >= required
            )
            return self._subset_opportunity(n, hand_size, required, qualifying)
        if hand_type == "STRAIGHT_FLUSH":
            required = max(
                max(1, int(rules.get("straight_size", 5) or 5)),
                max(1, int(rules.get("flush_size", 5) or 5)),
            )
            qualifying = sum(
                self._straight_combo_count(
                    counts,
                    required=required,
                    max_step=2 if rules.get("shortcut") else 1,
                )
                for counts in self._effective_suit_rank_counts(cards, rules).values()
            )
            return self._subset_opportunity(n, hand_size, required, qualifying)
        if hand_type == "FLUSH_HOUSE":
            qualifying = 0
            for counts in self._effective_suit_rank_counts(cards, rules).values():
                qualifying += sum(
                    comb(trips, 3) * comb(pair, 2)
                    for trip_rank, trips in counts.items()
                    for pair_rank, pair in counts.items()
                    if trip_rank != pair_rank and trips >= 3 and pair >= 2
                )
            return self._subset_opportunity(n, hand_size, 5, qualifying)
        if hand_type == "FLUSH_FIVE":
            qualifying = sum(
                comb(count, 5)
                for counts in self._effective_suit_rank_counts(cards, rules).values()
                for count in counts.values()
                if count >= 5
            )
            return self._subset_opportunity(n, hand_size, 5, qualifying)
        return 0.0

    @staticmethod
    def _owned_regular_cards(state) -> list:
        owned = getattr(state, "owned_deck", None)
        cards = list(owned if owned is not None else getattr(state, "deck", ()))
        return [
            card
            for card in cards
            if getattr(card, "enhancement", None) != "Stone"
        ]

    @classmethod
    def _straight_combo_count(
        cls,
        rank_counts: Counter,
        *,
        required: int,
        max_step: int,
    ) -> int:
        ranks = [rank for rank in rank_counts if rank in cls._RANK_ORDER]
        if len(ranks) < required:
            return 0

        qualifying = 0
        for rank_group in combinations(ranks, required):
            values = sorted(cls._RANK_ORDER[rank] for rank in rank_group)
            normal = all(
                1 <= current - previous <= max_step
                for previous, current in zip(values, values[1:])
            )
            ace_low = False
            if "A" in rank_group:
                ace_values = sorted(
                    1 if rank == "A" else cls._RANK_ORDER[rank]
                    for rank in rank_group
                )
                ace_low = all(
                    1 <= current - previous <= max_step
                    for previous, current in zip(ace_values, ace_values[1:])
                )
            if normal or ace_low:
                ways = 1
                for rank in rank_group:
                    ways *= int(rank_counts[rank])
                qualifying += ways
        return qualifying

    @classmethod
    def _effective_suit_rank_counts(cls, cards, rules) -> dict[str, Counter]:
        smeared = rules.get("smeared_suits")
        result = {suit: Counter() for suit in cls._SUITS}
        for card in cards:
            rank = str(getattr(card, "rank", ""))
            actual = str(getattr(card, "suit", ""))
            wild = getattr(card, "enhancement", None) == "Wild"
            for suit in cls._SUITS:
                matches = wild or actual == suit
                if not matches and isinstance(smeared, dict):
                    matches = smeared.get(actual) == smeared.get(suit)
                if matches:
                    result[suit][rank] += 1
        return result

    @staticmethod
    def _subset_opportunity(
        deck_size: int,
        hand_size: int,
        subset_size: int,
        qualifying_subsets: int,
    ) -> float:
        if subset_size <= 0 or deck_size < subset_size or hand_size < subset_size:
            return 0.0
        total_subsets = comb(deck_size, subset_size)
        if total_subsets <= 0 or qualifying_subsets <= 0:
            return 0.0
        subset_probability = min(
            1.0,
            float(qualifying_subsets) / float(total_subsets),
        )
        opportunities = max(1, comb(hand_size, subset_size))
        return min(1.0, 1.0 - (1.0 - subset_probability) ** opportunities)
