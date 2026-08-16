from games.balatro.joker import Joker, JokerContext


class DNAJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_PLAYED":
            return context

        cards = list(context.cards or [])
        if len(cards) != 1:
            return context

        round_counts = getattr(context.state, "round_hand_play_counts", {})
        if any(int(value or 0) > 0 for value in getattr(round_counts, "values", lambda: [])()):
            return context

        context.data.setdefault("dna_copy_sources", []).append(cards[0])
        return context
