from games.balatro.joker import Joker, JokerContext


class CardSharpJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.data.get("poker_hand_played_twice"):
            context.score.x_mult *= 3

        return context