from itertools import combinations

from games.balatro.consumable import ConsumableContext, TarotCard
from games.balatro.card import BalatroCard


class Strength(TarotCard):

    def __init__(self):

        super().__init__(
            "Strength"
        )

    def can_use(
        self,
        context: ConsumableContext
    ) -> bool:

        return len(context.cards) > 0

    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:

        for card in context.cards:

            if card.rank == "A":
                continue

            ranks = [
                "2", "3", "4", "5", "6",
                "7", "8", "9", "10",
                "J", "Q", "K", "A"
            ]

            card.rank = ranks[
                ranks.index(card.rank) + 1
            ]

        return context

    def get_target_cards(
        self,
        state
    ) -> list[list[BalatroCard]]:

        return [
            list(cards)
            for cards in combinations(
                state.hand,
                min(2, len(state.hand))
            )
        ]


TAROT_CARDS = {
    "Strength": Strength
}


def create_tarot(
    name: str
) -> TarotCard:

    return TAROT_CARDS[name]()