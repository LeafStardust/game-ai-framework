from games.balatro.joker import Joker, JokerContext


class CardSharpJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None or context.poker_hand is None:
            return context

        counts = getattr(context.state, "round_hand_play_counts", {})
        previous_plays = int(
            counts.get(
                context.poker_hand.value,
                counts.get(context.poker_hand, 0),
            )
            or 0
        )
        if previous_plays >= 1:
            context.score.x_mult *= 3

        return context
