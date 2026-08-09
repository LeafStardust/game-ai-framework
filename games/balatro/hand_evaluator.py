from collections import Counter

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
        "A": 14
    }

    def evaluate(
        self,
        cards: list[BalatroCard]
    ) -> PokerHand:

        if not cards:
            return PokerHand.HIGH_CARD

        ranks = [
            card.rank
            for card in cards
        ]

        counts = Counter(ranks)

        values = sorted(
            counts.values(),
            reverse=True
        )

        is_flush = self._is_flush(cards)
        is_straight = self._is_straight(cards)

        if is_flush and is_straight:
            return PokerHand.STRAIGHT_FLUSH

        if values[0] == 4:
            return PokerHand.FOUR_OF_A_KIND

        if values[0] == 3 and len(values) > 1 and values[1] == 2:
            return PokerHand.FULL_HOUSE

        if is_flush:
            return PokerHand.FLUSH

        if is_straight:
            return PokerHand.STRAIGHT

        if values[0] == 3:
            return PokerHand.THREE_OF_A_KIND

        if values[0] == 2:

            pairs = values.count(2)

            if pairs == 2:
                return PokerHand.TWO_PAIR

            return PokerHand.PAIR

        return PokerHand.HIGH_CARD

    def _is_flush(
        self,
        cards: list[BalatroCard]
    ) -> bool:

        if len(cards) != 5:
            return False

        suits = [
            card.suit
            for card in cards
        ]

        return len(set(suits)) == 1

    def _is_straight(
        self,
        cards: list[BalatroCard]
    ) -> bool:

        if len(cards) != 5:
            return False

        values = sorted(
            [
                self.RANK_ORDER[card.rank]
                for card in cards
            ]
        )

        if values == [2, 3, 4, 5, 14]:
            return True

        return values == list(
            range(
                values[0],
                values[0] + 5
            )
        )
