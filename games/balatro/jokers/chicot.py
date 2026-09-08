from games.balatro.joker import Joker, JokerContext


class ChicotJoker(Joker):
    """Model Chicot's queued Boss-disable request at ``setting_blind``.

    Vanilla does not disable the Blind synchronously inside Joker calculation.
    It queues ``G.GAME.blind:disable()`` and the event executes only after every
    Joker has received the same setting-blind context.  The environment lifecycle
    owner therefore consumes ``boss_disable_requests`` after the full Joker pass.
    """

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SELECTED":
            return context
        if not context.data.get("boss_blind", False):
            return context

        context.data["boss_disable_requests"] = (
            context.data.get("boss_disable_requests", 0) + 1
        )
        return context
