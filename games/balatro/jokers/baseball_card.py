from games.balatro.joker import Joker, JokerContext


class BaseballCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        context.data["rare_joker_triggers"] = (
            context.data.get("rare_joker_triggers", 0)
            + sum(
                getattr(joker, "rarity", None) == "Rare"
                for joker in getattr(context.state, "jokers", [])
            )
        )

        return context