import random

from games.balatro.joker import Joker, JokerContext


class SixthSenseJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        if len(context.cards) != 1:
            return context

        if context.cards[0].rank != "6":
            return context

        if context.data.get("sixth_sense_triggered"):
            return context

        context.data["sixth_sense_triggered"] = True
        context.data.setdefault(
            "destroyed_cards",
            []
        ).append(context.cards[0])

        context.data.setdefault(
            "created_consumables",
            []
        ).append(
            random.choice([
                "Familiar",
                "Grim",
                "Incantation",
                "Talisman",
                "Aura",
            ])
        )

        return context