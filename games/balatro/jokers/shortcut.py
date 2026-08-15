from games.balatro.joker import Joker, JokerContext


class ShortcutJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger not in {"", "HAND_RULES"}:
            return context
        context.data["shortcut"] = True
        return context
