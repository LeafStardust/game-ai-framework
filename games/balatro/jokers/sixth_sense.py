from games.balatro.joker import Joker, JokerContext


class SixthSenseJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        cards = list(context.cards or [])
        if len(cards) != 1 or str(getattr(cards[0], "rank", "")) != "6":
            return context

        counts = getattr(context.state, "round_hand_play_counts", None)
        if isinstance(counts, dict) and any(
            int(value or 0) > 0 for value in counts.values()
        ):
            return context
        if context.data.get("first_hand") is False:
            return context

        context.data.setdefault("destroyed_cards", []).append(cards[0])
        # Category marker only; live projection owns slot checks and destruction.
        context.data.setdefault("created_consumables", []).append("Spectral")
        return context
