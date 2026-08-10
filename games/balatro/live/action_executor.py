from games.balatro.actions import BalatroAction
from games.balatro.live.interfaces import BalatroActionExecutor
from games.balatro.live.protocol import (
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


class DefaultBalatroActionExecutor(BalatroActionExecutor):

    def command_for(
        self,
        action: BalatroAction,
        snapshot: LiveBalatroSnapshot
    ) -> LiveBalatroCommand:
        payload: dict = {}

        if action.cards:
            payload["cards"] = [
                self._object_id(card)
                for card in action.cards
            ]

        if action.target is not None:
            payload["target"] = self._object_id(
                action.target
            )

        return LiveBalatroCommand(
            sequence=snapshot.sequence,
            action=action.name,
            payload=payload,
        )

    @staticmethod
    def _object_id(value) -> str:
        if isinstance(value, dict):
            live_id = value.get("id")
        else:
            live_id = getattr(value, "live_id", None)

        if not live_id:
            raise ValueError(
                "live Balatro objects require a live_id"
            )

        return str(live_id)
