from games.balatro.joker import Joker, JokerContext


class BrainstormJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        jokers = getattr(
            context.state,
            "jokers",
            []
        )

        if not jokers:
            return context

        context.data["copy_joker"] = jokers[0]

        return context