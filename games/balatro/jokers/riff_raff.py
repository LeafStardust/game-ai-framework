from games.balatro.joker import Joker, JokerContext


class RiffRaffJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SELECTED":
            return context

        context.data["create_random_jokers"] = 2

        return context