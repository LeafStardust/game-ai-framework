from games.balatro.joker import Joker, JokerContext


class WeeJoker(Joker):

    def __init__(self):
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.trigger == "CARD_SCORED":
            card = context.data.get("current_scoring_card")
            if card is not None and card.rank == "2":
                self.chips += 8
            return context

        if context.trigger == "HAND_SCORED":
            context.score.chips += self.chips
            return context

        # Preserve standalone semantic probes that do not model explicit scoring
        # phases: grow from scored 2s, then contribute the resulting chip total.
        scoring_cards = context.data.get("scoring_cards", context.cards)
        twos = sum(
            card.rank == "2"
            for card in scoring_cards
        )
        self.chips += twos * 8
        context.score.chips += self.chips
        return context
