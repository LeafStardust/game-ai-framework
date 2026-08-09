from games.balatro.joker import Joker, JokerContext


class LuchadorJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BOSS_BLIND_SELECTED":
            return context

        context.data["boss_blind_disabled"] = True

        return context