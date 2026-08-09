from games.balatro.joker import Joker, JokerContext


class DriversLicenseJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        enhanced_cards = sum(
            getattr(card, "enhancement", None) is not None
            for card in context.state.deck
        )

        if enhanced_cards >= 16:
            context.score.x_mult *= 3

        return context