from games.balatro.joker import Joker, JokerContext


class SuperpositionJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        has_ace = any(card.rank == "A" for card in context.cards)
        has_straight = context.data.get("straight", False)

        if has_ace and has_straight:
            context.data.setdefault(
                "created_tarot_cards",
                []
            ).append("Random")

        return context