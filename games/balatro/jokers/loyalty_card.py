from games.balatro.joker import Joker, JokerContext


class LoyaltyCardJoker(Joker):

    def __init__(self):
        self.hands = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            self.hands += 1
            ready = self.hands > 0 and self.hands % 6 == 0
            context.data["loyalty_card_ready"] = ready
            setattr(context.state, "_loyalty_card_ready", ready)
            return context

        if context.trigger == "HAND_SCORED" and context.score is not None:
            ready = context.data.get(
                "loyalty_card_ready",
                bool(getattr(context.state, "_loyalty_card_ready", False)),
            )
            if ready:
                context.score.x_mult *= 4

            if hasattr(context.state, "_loyalty_card_ready"):
                delattr(context.state, "_loyalty_card_ready")

        return context
