from games.balatro.joker import Joker, JokerContext


class FacelessJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        face_cards = sum(
            card.rank in {"J", "Q", "K"}
            for card in context.cards
        )

        if face_cards >= 3:
            context.data["money"] = (
                context.data.get("money", 0) + 5
            )

        return context