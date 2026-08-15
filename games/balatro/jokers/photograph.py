from games.balatro.joker import Joker, JokerContext


class PhotographJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        if scoring_cards and scoring_cards[0].rank in {"J", "Q", "K"}:
            context.score.x_mult *= 2

        return context
