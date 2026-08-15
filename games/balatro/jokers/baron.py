from games.balatro.joker import Joker, JokerContext


class BaronJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.trigger == "HELD_CARD":
            card = context.data.get("held_card")
            if card is not None and card.rank == "K":
                context.score.x_mult *= 1.5
            return context

        if context.trigger:
            return context

        # Preserve standalone semantic probes outside the explicit scoring phases.
        kings = sum(
            card.rank == "K"
            for card in context.held_cards
        )
        context.score.x_mult *= 1.5 ** kings
        return context
