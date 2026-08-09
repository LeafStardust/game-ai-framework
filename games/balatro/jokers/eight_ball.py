import random

from games.balatro.joker import Joker, JokerContext


class EightBallJoker(Joker):

    TAROT_CARDS = [
        "The Fool",
        "The Magician",
        "The High Priestess",
        "The Empress",
        "The Emperor",
        "The Hierophant",
        "The Lovers",
        "The Chariot",
        "Justice",
        "The Hermit",
        "The Wheel of Fortune",
        "Strength",
        "The Hanged Man",
        "Death",
        "Temperance",
        "The Devil",
        "The Tower",
        "The Star",
        "The Moon",
        "The Sun",
        "Judgement",
        "The World",
    ]

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        eights = sum(
            card.rank == "8"
            for card in context.cards
        )

        if eights and random.random() < 0.25:
            context.data.setdefault(
                "created_consumables",
                []
            ).append(random.choice(self.TAROT_CARDS))

        return context