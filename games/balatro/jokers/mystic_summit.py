from games.balatro.joker import Joker, JokerContext


class MysticSummitJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.data.get("discards_remaining", 0) == 0:
            context.score.mult += 15

        return context