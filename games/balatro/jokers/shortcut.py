from games.balatro.joker import Joker, JokerContext


class ShortcutJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.data.get("shortcut"):
            return context

        context.data["shortcut"] = True

        return context