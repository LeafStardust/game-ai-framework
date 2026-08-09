from games.balatro.joker import Joker, JokerContext


class DNAJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        if len(context.cards) != 1:
            return context

        context.data.setdefault(
            "copied_cards",
            []
        ).append(context.cards[0])

        return context