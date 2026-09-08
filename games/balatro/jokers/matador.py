from games.balatro.boss_trigger import matador_boss_hand_triggered
from games.balatro.joker import Joker, JokerContext


class MatadorJoker(Joker):

    REWARD = 8

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        result = matador_boss_hand_triggered(
            context.state,
            context.poker_hand,
            context.cards,
        )
        if not result.resolvable or not result.triggered:
            return context

        if context.state is not None:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + self.REWARD
            )
        context.data["money"] = (
            int(context.data.get("money", 0) or 0)
            + self.REWARD
        )
        return context
