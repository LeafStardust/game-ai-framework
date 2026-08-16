from __future__ import annotations

from collections import Counter
from itertools import combinations

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand


class HandEvaluator:

    RANK_ORDER = {
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

    def evaluate(
        self,
        cards: list[BalatroCard],
        rules: dict | None = None,
    ) -> PokerHand:
        rules = dict(rules or {})
        regular = self._regular_cards(cards)
        if not regular:
            return PokerHand.HIGH_CARD

        ranks = [card.rank for card in regular]
        counts = Counter(ranks)
        values = sorted(counts.values(), reverse=True)

        flush_cards = self._flush_cards(regular, rules)
        straight_cards = self._straight_cards(regular, rules)
        five_of_a_kind = values[0] >= 5
        full_house = (
            values[0] >= 3
            and len(values) > 1
            and values[1] >= 2
        )

        # Balatro's secret hands outrank their ordinary components. Flush Five is
        # simultaneously a flush and Five of a Kind; Flush House is simultaneously
        # a flush and Full House.
        if five_of_a_kind and flush_cards:
            return PokerHand.FLUSH_FIVE

        if full_house and flush_cards:
            return PokerHand.FLUSH_HOUSE

        # With Four Fingers, the straight and flush portions of a Straight Flush
        # may be supplied by different four-card subsets of the five played cards.
        if flush_cards and straight_cards:
            return PokerHand.STRAIGHT_FLUSH

        if five_of_a_kind:
            return PokerHand.FIVE_OF_A_KIND

        if values[0] >= 4:
            return PokerHand.FOUR_OF_A_KIND

        if full_house:
            return PokerHand.FULL_HOUSE

        if flush_cards:
            return PokerHand.FLUSH

        if straight_cards:
            return PokerHand.STRAIGHT

        if values[0] == 3:
            return PokerHand.THREE_OF_A_KIND

        if values[0] == 2:
            pairs = values.count(2)
            if pairs >= 2:
                return PokerHand.TWO_PAIR
            return PokerHand.PAIR

        return PokerHand.HIGH_CARD

    def contains(
        self,
        cards: list[BalatroCard],
        hand: PokerHand,
        rules: dict | None = None,
    ) -> bool:
        """Return whether played cards contain one poker-hand component.

        Balatro distinguishes a hand being classified as one type from containing
        another type. This predicate is shared by Joker mechanics so passive hand
        rules such as Four Fingers, Shortcut and Smeared Joker are interpreted in
        exactly the same way as hand recognition and scoring-card selection.
        """
        rules = dict(rules or {})
        regular = self._regular_cards(cards)
        if not regular:
            return False

        counts = Counter(str(card.rank) for card in regular)
        values = sorted(counts.values(), reverse=True)
        flush = bool(self._flush_cards(regular, rules))
        full_house = (
            any(count >= 3 for count in values)
            and sum(count >= 2 for count in values) >= 2
        )
        five_of_a_kind = any(count >= 5 for count in values)

        if hand == PokerHand.HIGH_CARD:
            return True
        if hand == PokerHand.PAIR:
            return any(count >= 2 for count in values)
        if hand == PokerHand.TWO_PAIR:
            return sum(count >= 2 for count in values) >= 2
        if hand == PokerHand.THREE_OF_A_KIND:
            return any(count >= 3 for count in values)
        if hand == PokerHand.FOUR_OF_A_KIND:
            return any(count >= 4 for count in values)
        if hand == PokerHand.FIVE_OF_A_KIND:
            return five_of_a_kind
        if hand == PokerHand.FULL_HOUSE:
            return full_house
        if hand == PokerHand.FLUSH_HOUSE:
            return full_house and flush
        if hand == PokerHand.FLUSH_FIVE:
            return five_of_a_kind and flush
        if hand == PokerHand.STRAIGHT:
            return bool(self._straight_cards(regular, rules))
        if hand == PokerHand.FLUSH:
            return flush
        if hand == PokerHand.STRAIGHT_FLUSH:
            return bool(
                self._straight_cards(regular, rules)
                and flush
            )
        return self.evaluate(regular, rules=rules) == hand

    def scoring_cards(
        self,
        hand: PokerHand,
        cards: list[BalatroCard],
        rules: dict | None = None,
    ) -> list[BalatroCard]:
        """Return the exact played cards that Balatro treats as scoring cards."""
        rules = dict(rules or {})
        played = list(cards or [])
        if not played:
            return []

        if rules.get("all_cards_score"):
            return played

        stones = [card for card in played if self._is_stone(card)]
        regular = [card for card in played if not self._is_stone(card)]
        if not regular:
            return stones

        counts = Counter(str(card.rank) for card in regular)

        if hand == PokerHand.STRAIGHT_FLUSH:
            selected = self._union_in_played_order(
                regular,
                self._straight_cards(regular, rules),
                self._flush_cards(regular, rules),
            )
        elif hand in {PokerHand.FLUSH_HOUSE, PokerHand.FLUSH_FIVE}:
            # These categories require all five structural cards, so all regular
            # cards in the recognized five-card play score.
            selected = regular
        elif hand == PokerHand.FLUSH:
            selected = self._flush_cards(regular, rules)
        elif hand == PokerHand.STRAIGHT:
            selected = self._straight_cards(regular, rules)
        elif hand == PokerHand.HIGH_CARD:
            highest = max(
                regular,
                key=lambda card: self.RANK_ORDER.get(str(card.rank), -1),
            )
            selected = [highest]
        elif hand == PokerHand.PAIR:
            pair_rank = next(
                (rank for rank, count in counts.items() if count >= 2),
                None,
            )
            selected = [card for card in regular if str(card.rank) == pair_rank][:2]
        elif hand == PokerHand.TWO_PAIR:
            pair_ranks = {
                rank for rank, count in counts.items() if count >= 2
            }
            selected = [card for card in regular if str(card.rank) in pair_ranks][:4]
        elif hand == PokerHand.THREE_OF_A_KIND:
            trip_rank = next(
                (rank for rank, count in counts.items() if count >= 3),
                None,
            )
            selected = [card for card in regular if str(card.rank) == trip_rank][:3]
        elif hand == PokerHand.FOUR_OF_A_KIND:
            quad_rank = next(
                (rank for rank, count in counts.items() if count >= 4),
                None,
            )
            selected = [card for card in regular if str(card.rank) == quad_rank][:4]
        elif hand == PokerHand.FIVE_OF_A_KIND:
            five_rank = next(
                (rank for rank, count in counts.items() if count >= 5),
                None,
            )
            selected = [card for card in regular if str(card.rank) == five_rank][:5]
        else:
            selected = regular

        selected_ids = {id(card) for card in selected}
        selected.extend(card for card in stones if id(card) not in selected_ids)
        return selected

    def _flush_cards(self, cards: list[BalatroCard], rules: dict) -> list[BalatroCard]:
        required = max(1, int(rules.get("flush_size", 5) or 5))
        if len(cards) < required:
            return []

        best: list[BalatroCard] = []
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades"):
            matching = [
                card
                for card in cards
                if self._matches_suit(card, suit, rules)
            ]
            if len(matching) >= required and len(matching) > len(best):
                best = matching
        return best

    def _straight_cards(self, cards: list[BalatroCard], rules: dict) -> list[BalatroCard]:
        required = max(1, int(rules.get("straight_size", 5) or 5))
        if len(cards) < required:
            return []

        shortcut = bool(rules.get("shortcut"))
        max_step = 2 if shortcut else 1
        rank_values = {
            str(card.rank): self.RANK_ORDER[str(card.rank)]
            for card in cards
            if str(card.rank) in self.RANK_ORDER
        }
        if len(rank_values) < required:
            return []

        value_sets: list[dict[str, int]] = [rank_values]
        if "A" in rank_values:
            ace_low = dict(rank_values)
            ace_low["A"] = 1
            value_sets.append(ace_low)

        qualifying_ranks: set[str] = set()
        for values_by_rank in value_sets:
            for rank_combo in combinations(values_by_rank, required):
                ordered = sorted(values_by_rank[rank] for rank in rank_combo)
                if all(
                    1 <= current - previous <= max_step
                    for previous, current in zip(ordered, ordered[1:])
                ):
                    qualifying_ranks.update(rank_combo)

        if not qualifying_ranks:
            return []
        return [card for card in cards if str(card.rank) in qualifying_ranks]

    @staticmethod
    def _is_stone(card: BalatroCard) -> bool:
        return getattr(card, "enhancement", None) == "Stone"

    def _regular_cards(self, cards) -> list[BalatroCard]:
        return [card for card in list(cards or []) if not self._is_stone(card)]

    @staticmethod
    def _matches_suit(card: BalatroCard, suit: str, rules: dict) -> bool:
        if getattr(card, "enhancement", None) == "Stone":
            return False
        if getattr(card, "enhancement", None) == "Wild":
            return True

        actual = str(getattr(card, "suit", ""))
        if actual == suit:
            return True

        smeared = rules.get("smeared_suits")
        if not isinstance(smeared, dict):
            return False
        return smeared.get(actual) == smeared.get(suit)

    @staticmethod
    def _union_in_played_order(cards, *groups) -> list[BalatroCard]:
        selected_ids = {
            id(card)
            for group in groups
            for card in group
        }
        return [card for card in cards if id(card) in selected_ids]
