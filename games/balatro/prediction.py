import random

from framework.core.action import Action
from framework.core.state import GameState

from games.balatro.environment import BalatroEnvironment


class BalatroFutureStatePredictor:

    def __init__(
        self,
        environment: BalatroEnvironment,
        seed: int | None = None
    ):
        self.environment = environment
        self.rng = random.Random(seed)

    def predict(
        self,
        action: Action,
        samples: int = 1
    ) -> list[GameState]:

        if samples < 1:
            raise ValueError("samples must be at least 1")

        states = []

        for _ in range(samples):

            environment = self.environment.copy()

            self.rng.shuffle(
                environment.state.deck
            )

            environment.execute_action(
                action.copy()
            )

            states.append(
                environment.get_state()
            )

        return states
