import random

from games.balatro.joker import Joker, JokerContext


class CartomancerJoker(Joker):

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
        if context.trigger != "BLIND_SELECTED":
            return context

        if context.data.get("consumable_slots_full", False):
            return context

        tarot = random.choice(self.TAROT_CARDS)

        context.data.setdefault(
            "created_consumables",
            []
        ).append(tarot)

        return context