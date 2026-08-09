from games.balatro.joker import Joker, JokerContext


class MidasMaskJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        for card in context.cards:
            if card.rank in {"J", "Q", "K"}:
                card.enhancement = "Gold"

        return context