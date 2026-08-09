from games.balatro.joker import Joker, JokerContext


class HikerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        for card in context.cards:
            card.permanent_bonus = (
                getattr(card, "permanent_bonus", 0) + 5
            )

        return context