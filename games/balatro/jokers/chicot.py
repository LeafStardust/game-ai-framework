from games.balatro.joker import Joker, JokerContext


class ChicotJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.data.get("boss_blind", False):
            context.data["disable_boss_blind"] = True

        return context