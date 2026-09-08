from games.balatro.joker import Joker, JokerContext


class ShootTheMoonJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.trigger == "HELD_CARD":
            card = context.data.get("held_card")
            if card is not None and card.rank == "Q":
                context.score.mult += 13
            return context

        if context.trigger:
            return context

        # Preserve standalone semantic probes outside the explicit scoring phases.
        queens = sum(
            card.rank == "Q"
            for card in context.held_cards
        )
        context.score.mult += queens * 13
        return context
