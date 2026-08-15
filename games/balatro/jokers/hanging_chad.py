from games.balatro.joker import Joker, JokerContext


class HangingChadJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_PLAYED":
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        if not scoring_cards:
            return context

        first = scoring_cards[0]
        by_card = context.data.setdefault("retrigger_by_card_id", {})
        by_card[id(first)] = int(by_card.get(id(first), 0) or 0) + 2

        return context
