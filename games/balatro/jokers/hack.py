from games.balatro.joker import Joker, JokerContext


class HackJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_PLAYED":
            return context

        ranks = {"2", "3", "4", "5"}
        scoring_cards = context.data.get("scoring_cards", context.cards)
        by_card = context.data.setdefault("retrigger_by_card_id", {})

        for card in scoring_cards:
            if card.rank not in ranks:
                continue
            by_card[id(card)] = int(by_card.get(id(card), 0) or 0) + 1

        return context
