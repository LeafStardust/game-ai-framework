from games.balatro.joker import Joker, JokerContext


class LoyaltyCardJoker(Joker):

    def __init__(self):
        self.hands = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            self.hands += 1
            ready = self.hands > 0 and self.hands % 6 == 0
            if ready:
                context.data["loyalty_card_ready"] = True
                if context.score is not None:
                    context.score.x_mult *= 4
            return context

        if (
            context.trigger == "HAND_SCORED"
            and context.score is not None
            and context.data.get("loyalty_card_ready", False)
        ):
            context.score.x_mult *= 4

        return context
