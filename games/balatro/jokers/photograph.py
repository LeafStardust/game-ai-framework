from games.balatro.joker import Joker, JokerContext


class PhotographJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        if not scoring_cards:
            return context

        first = scoring_cards[0]
        if first.rank not in {"J", "Q", "K"}:
            return context

        triggers = sum(card is first for card in scoring_cards)
        context.score.x_mult *= 2 ** triggers

        return context
