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
            # Deterministic capability markers: each scored 8 is one independent
            # Tarot-generation attempt. Live projection owns the exact 1-in-4 RNG.
            context.data.setdefault("created_consumables", []).extend(
                ["Random Tarot attempt"] * attempts
            )
        return context
