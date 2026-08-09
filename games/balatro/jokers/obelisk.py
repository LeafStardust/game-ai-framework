from games.balatro.joker import Joker, JokerContext


class ObeliskJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        most_played_hand = context.data.get("most_played_hand")

        if context.poker_hand == most_played_hand:
            self.x_mult = 1.0
        else:
            self.x_mult += 0.2

        context.score.x_mult *= self.x_mult

        return context