from games.balatro.joker import Joker, JokerContext


class SupernovaJoker(Joker):
    """Add Mult equal to how often the scored poker hand has been played.

    Committed Play supplies the run-wide count after recording the hand.
    Prospective scoring adds one to the history visible before the play.
    """

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None or context.poker_hand is None:
            return context

        play_count = context.data.get("scoring_hand_play_count")
        if play_count is None:
            hand_name = getattr(context.poker_hand, "value", context.poker_hand)
            counts = getattr(context.state, "hand_play_counts", {}) or {}
            play_count = int(counts.get(str(hand_name), 0)) + 1
        context.score.mult += play_count

        return context
