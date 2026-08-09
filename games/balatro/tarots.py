from itertools import combinations

from games.balatro.consumable import ConsumableContext, TarotCard
from games.balatro.card import BalatroCard


class Strength(TarotCard):

    def __init__(self):
        super().__init__("Strength")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        ranks = [
            "2", "3", "4", "5", "6",
            "7", "8", "9", "10",
            "J", "Q", "K", "A"
        ]

        for card in context.cards:
            if card.rank != "A":
                card.rank = ranks[ranks.index(card.rank) + 1]

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Magician(TarotCard):

    def __init__(self):
        super().__init__("The Magician")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.enhancement = "Lucky"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Empress(TarotCard):

    def __init__(self):
        super().__init__("The Empress")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.enhancement = "Mult"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Hierophant(TarotCard):

    def __init__(self):
        super().__init__("The Hierophant")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.enhancement = "Bonus"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Lovers(TarotCard):

    def __init__(self):
        super().__init__("The Lovers")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].enhancement = "Wild"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            [card]
            for card in state.hand
        ]


class Chariot(TarotCard):

    def __init__(self):
        super().__init__("The Chariot")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].enhancement = "Steel"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            [card]
            for card in state.hand
        ]


class Justice(TarotCard):

    def __init__(self):
        super().__init__("Justice")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].enhancement = "Glass"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            [card]
            for card in state.hand
        ]


class Devil(TarotCard):

    def __init__(self):
        super().__init__("The Devil")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].enhancement = "Gold"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            [card]
            for card in state.hand
        ]


class Tower(TarotCard):

    def __init__(self):
        super().__init__("The Tower")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 1
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].enhancement = "Stone"
        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            [card]
            for card in state.hand
        ]


class Star(TarotCard):

    def __init__(self):
        super().__init__("The Star")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 3
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.suit = "Diamonds"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2, 3)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Moon(TarotCard):

    def __init__(self):
        super().__init__("The Moon")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 3
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.suit = "Clubs"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2, 3)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Sun(TarotCard):

    def __init__(self):
        super().__init__("The Sun")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 3
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.suit = "Hearts"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2, 3)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class World(TarotCard):

    def __init__(self):
        super().__init__("The World")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 3
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            card.suit = "Spades"

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2, 3)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


TAROT_CARDS = {
    "Strength": Strength,
    "The Magician": Magician,
    "The Empress": Empress,
    "The Hierophant": Hierophant,
    "The Lovers": Lovers,
    "The Chariot": Chariot,
    "Justice": Justice,
    "The Devil": Devil,
    "The Tower": Tower,
    "The Star": Star,
    "The Moon": Moon,
    "The Sun": Sun,
    "The World": World,
}


def create_tarot(name: str) -> TarotCard:
    return TAROT_CARDS[name]()


def random_tarot(rng) -> TarotCard:
    name = rng.choice(list(TAROT_CARDS))
    return create_tarot(name)