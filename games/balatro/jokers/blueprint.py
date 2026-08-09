from games.balatro.joker import Joker, JokerContext


class BlueprintJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        jokers = getattr(context.state, "jokers", [])

        try:
            index = jokers.index(self)
        except ValueError:
            return context

        if index + 1 < len(jokers):
            context.data["copy_joker"] = jokers[index + 1]

        return context