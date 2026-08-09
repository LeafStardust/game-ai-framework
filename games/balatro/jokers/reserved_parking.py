import random

from games.balatro.joker import Joker, JokerContext


class ReservedParkingJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        face_cards = sum(
            card.rank in {"J", "Q", "K"}
            for card in getattr(context.state, "hand", [])
        )

        for _ in range(face_cards):
            if random.random() < 0.25:
                context.data["money"] = (
                    context.data.get("money", 0) + 1
                )

        return context