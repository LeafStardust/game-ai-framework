from framework.core.action import Action

from games.balatro.environment import BalatroEnvironment
from games.balatro.planning import BalatroPlan


class TacticalPathCommitment:

    def __init__(self):
        self.actions: list[Action] = []

    @property
    def active(self) -> bool:
        return bool(self.actions)

    def commit(
        self,
        plan: BalatroPlan
    ) -> None:
        self.actions = [
            action.copy()
            for action in plan.actions
        ]

    def clear(self) -> None:
        self.actions.clear()

    def next_action(
        self,
        environment: BalatroEnvironment
    ) -> Action | None:

        if not self.actions:
            return None

        planned = self.actions[0]

        for available in environment.get_actions():
            if self._matches(planned, available):
                self.actions.pop(0)
                return available

        self.clear()
        return None

    def _matches(
        self,
        planned: Action,
        available: Action
    ) -> bool:
        return (
            planned.name == available.name
            and getattr(planned, "cards", []) == getattr(available, "cards", [])
            and getattr(planned, "target", None) == getattr(available, "target", None)
        )
