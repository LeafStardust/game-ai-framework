from games.balatro.joker import Joker, JokerContext


class WalkieTalkieJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        count = sum(
            str(getattr(card, "rank", "")) in {"10", "4"}
            for card in scoring_cards
        )
        context.score.chips += count * 10
        context.score.mult += count * 4
        return context
