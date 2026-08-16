from games.balatro.joker import Joker, JokerContext


class DriversLicenseJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        owned_deck = getattr(context.state, "owned_deck", None)
        if owned_deck is None:
            return context

        enhanced = sum(
            getattr(card, "enhancement", None) is not None
            for card in owned_deck
        )
        if enhanced >= 16:
            context.score.x_mult *= 3

        return context
