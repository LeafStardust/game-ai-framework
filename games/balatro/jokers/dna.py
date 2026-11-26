from games.balatro.joker import Joker, JokerContext


class DNAJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_PLAYED":
            return context

        cards = list(context.cards or [])
        if len(cards) != 1:
            return context

        first_hand = context.data.get("first_hand")
        if first_hand is None:
            round_counts = getattr(context.state, "round_hand_play_counts", {})
            first_hand = not any(
                int(value or 0) > 0 for value in getattr(round_counts, "values", lambda: [])()
            )
        if first_hand is not True:
            return context

        context.data.setdefault("dna_copy_sources", []).append(cards[0])
        return context
