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

        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

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
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(
                state.hand,
                size
            )
        ]


class Magician(TarotCard):

    def __init__(self):

        super().__init__(
            "The Magician"
        )

    def can_use(
        self,
        context: ConsumableContext
    ) -> bool:

        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:

        for card in context.cards:
            card.enhancement = "Lucky"

        return context

    def get_target_cards(
        self,
        state
    ) -> list[list[BalatroCard]]:

        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(
                state.hand,
                size
            )
        ]


class Empress(TarotCard):

    def __init__(self):

        super().__init__(
            "The Empress"
        )

    def can_use(
        self,
        context: ConsumableContext
    ) -> bool:

        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:

        for card in context.cards:
            card.enhancement = "Mult"

        return context

    def get_target_cards(
        self,
        state
    ) -> list[list[BalatroCard]]:

        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(
                state.hand,
                size
            )
        ]


TAROT_CARDS = {
    "Strength": Strength,
    "The Magician": Magician,
    "The Empress": Empress
}


def create_tarot(
    name: str
) -> TarotCard:

    return TAROT_CARDS[name]()


def random_tarot(
    rng
) -> TarotCard:

    name = rng.choice(
        list(TAROT_CARDS)
    )

    return create_tarot(
        name
    )