from games.balatro.joker import Joker, JokerContext


class TribouletJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        matches = sum(
            card.rank in {"K", "Q"}
            for card in scoring_cards
        )

        context.score.x_mult *= 2 ** matches

        return context
