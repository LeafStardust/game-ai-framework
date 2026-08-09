from games.balatro.joker import Joker, JokerContext


class SeeingDoubleJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None:
            return context

        has_club = any(
            card.suit == "Clubs"
            for card in context.cards
        )

        has_other_suit = any(
            card.suit != "Clubs"
            for card in context.cards
        )

        if has_club and has_other_suit:
            context.score.x_mult *= 2

        return context