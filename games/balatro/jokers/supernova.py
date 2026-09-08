from games.balatro.joker import Joker, JokerContext


class SupernovaJoker(Joker):
    """Add Mult equal to how often the scored poker hand has been played.

    ``state.hand_play_counts`` is public run history observed before the candidate
    hand is played. Scoring a prospective hand therefore contributes one additional
    play for that hand type. The Joker has no fixed poker-hand constructor state.
    """

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None or context.poker_hand is None:
            return context

        hand_name = getattr(context.poker_hand, "value", context.poker_hand)
        counts = getattr(context.state, "hand_play_counts", {}) or {}
        previous_plays = int(counts.get(str(hand_name), 0))
        context.score.mult += previous_plays + 1

        return context
