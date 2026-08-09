from games.balatro.joker import Joker, JokerContext


class ErosionJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        deck = context.data.get("deck", [])
        target_size = context.data.get("deck_target_size", 52)

        missing = max(target_size - len(deck), 0)

        context.score.mult += missing * 4

        return context