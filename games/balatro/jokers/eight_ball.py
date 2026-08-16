from games.balatro.joker import Joker, JokerContext


class EightBallJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        scoring_cards = context.data.get("scoring_cards")
        cards = list(scoring_cards if scoring_cards is not None else context.cards or [])
        attempts = sum(
            str(getattr(card, "rank", "")) == "8"
            and not bool(getattr(card, "debuffed", False))
            for card in cards
        )
        if attempts:
            context.data["eight_ball_attempts"] = (
                int(context.data.get("eight_ball_attempts", 0) or 0) + attempts
            )
        return context
