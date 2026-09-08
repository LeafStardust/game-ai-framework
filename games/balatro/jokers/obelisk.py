from games.balatro.joker import Joker, JokerContext


class ObeliskJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        most_played_hands = context.data.get("most_played_hands")
        if most_played_hands is None:
            most_played_hand = context.data.get("most_played_hand")
            most_played_hands = (
                {most_played_hand}
                if most_played_hand is not None
                else set()
            )

        if context.poker_hand in most_played_hands:
            self.x_mult = 1.0
        else:
            self.x_mult += 0.2

        context.score.x_mult *= self.x_mult
        return context
