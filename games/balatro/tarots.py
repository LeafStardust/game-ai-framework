from itertools import combinations

from games.balatro.card import BalatroCard
from games.balatro.consumable import ConsumableContext, TarotCard
from games.balatro.planets import create_planet, random_planet


class Fool(TarotCard):

    def __init__(self):
        super().__init__("The Fool")

    def can_use(self, context: ConsumableContext) -> bool:
        return context.target is not None

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.data["copy"] = context.target
        return context


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


class HighPriestess(TarotCard):

    def __init__(self):
        super().__init__("The High Priestess")

    def can_use(self, context: ConsumableContext) -> bool:
        return True

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.data["created"] = [
            random_planet(context.data["rng"])
            for _ in range(2)
        ]

        return context


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


class Emperor(TarotCard):

    def __init__(self):
        super().__init__("The Emperor")

    def can_use(self, context: ConsumableContext) -> bool:
        return True

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.data["created"] = [
            context.data["random_tarot"]()
            for _ in range(2)
        ]

        return context


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
        return [[card] for card in state.hand]


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
        return [[card] for card in state.hand]


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
        return [[card] for card in state.hand]


class Hermit(TarotCard):

    def __init__(self):
        super().__init__("The Hermit")

    def can_use(self, context: ConsumableContext) -> bool:
        return context.state.money > 0

    def use(self, context: ConsumableContext) -> ConsumableContext:
        money_before = context.state.money
        gain = min(money_before, 20)
        context.state.money += gain
        context.data["money_before"] = money_before
        context.data["money_after"] = context.state.money
        context.data["money"] = gain

        return context


class WheelOfFortune(TarotCard):

    def __init__(self):
        super().__init__("The Wheel of Fortune")

    def can_use(self, context: ConsumableContext) -> bool:
        return bool(context.state.jokers)

    def use(self, context: ConsumableContext) -> ConsumableContext:
        result = context.data["rng"].random()

        if result < 0.25:
            edition = context.data["rng"].choice(
                ["Foil", "Holographic", "Polychrome"]
            )
            context.target.edition = edition
            context.data["edition"] = edition
        else:
            context.data["edition"] = None

        return context


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


class HangedMan(TarotCard):

    def __init__(self):
        super().__init__("The Hanged Man")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            0 < len(context.cards) <= 2
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        for card in context.cards:
            if card in context.state.hand:
                context.state.hand.remove(card)
                context.state.discard_pile.append(card)

        context.data["destroyed"] = list(context.cards)

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for size in (1, 2)
            if size <= len(state.hand)
            for cards in combinations(state.hand, size)
        ]


class Death(TarotCard):

    def __init__(self):
        super().__init__("Death")

    def can_use(self, context: ConsumableContext) -> bool:
        return (
            len(context.cards) == 2
            and context.has_valid_cards()
        )

    def use(self, context: ConsumableContext) -> ConsumableContext:
        source, target = context.cards
        source.rank = target.rank
        source.suit = target.suit
        source.enhancement = target.enhancement
        source.edition = target.edition
        source.seal = target.seal

        context.data["converted"] = source

        return context

    def get_target_cards(self, state) -> list[list[BalatroCard]]:
        return [
            list(cards)
            for cards in combinations(state.hand, 2)
        ]


class Temperance(TarotCard):

    def __init__(self):
        super().__init__("Temperance")

    def can_use(self, context: ConsumableContext) -> bool:
        return bool(context.state.jokers)

    def use(self, context: ConsumableContext) -> ConsumableContext:
        total = sum(
            max(0, int(getattr(joker, "sell_value", 0)))
            for joker in context.state.jokers
        )
        gain = min(total, 50)
        context.state.money += gain
        context.data["money"] = gain

        return context


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
        return [[card] for card in state.hand]


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
        return [[card] for card in state.hand]


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


class Judgement(TarotCard):

    def __init__(self):
        super().__init__("Judgement")

    def can_use(self, context: ConsumableContext) -> bool:
        return len(context.state.jokers) < 5

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.data["create_joker"] = True
        context.data["joker"] = (
            context.data["random_joker"]()
        )

        return context


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
    "The Fool": Fool,
    "The Magician": Magician,
    "The High Priestess": HighPriestess,
    "The Empress": Empress,
    "The Emperor": Emperor,
    "The Hierophant": Hierophant,
    "The Lovers": Lovers,
    "The Chariot": Chariot,
    "Justice": Justice,
    "The Hermit": Hermit,
    "The Wheel of Fortune": WheelOfFortune,
    "Strength": Strength,
    "The Hanged Man": HangedMan,
    "Death": Death,
    "Temperance": Temperance,
    "The Devil": Devil,
    "The Tower": Tower,
    "The Star": Star,
    "The Moon": Moon,
    "The Sun": Sun,
    "Judgement": Judgement,
    "The World": World,
}


def create_tarot(name: str) -> TarotCard:
    return TAROT_CARDS[name]()


def random_tarot(rng) -> TarotCard:
    return create_tarot(
        rng.choice(list(TAROT_CARDS))
    )