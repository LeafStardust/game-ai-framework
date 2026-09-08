from framework.agent.agent import Agent
from framework.core.game import Game
from framework.core.experience import Experience
from framework.config.config import FrameworkConfig
from framework.logging.logger import get_logger
from framework.metrics.metrics import Metrics
from framework.events.event import EventManager


class GameRunner:
    """
    Handles the execution loop between an agent and a game.
    """

    def __init__(
        self,
        game: Game,
        agent: Agent,
        config: FrameworkConfig | None = None
    ):
        self.game: Game = game
        self.agent: Agent = agent
        self.config: FrameworkConfig = config or FrameworkConfig()

        self.history: list[Experience] = []
        self.metrics = Metrics()
        self.events = EventManager()
        self.logger = get_logger(__name__)


    def run(self) -> float:

        environment = self.game.environment

        environment.reset()

        self.logger.info("Game run started")

        self.events.emit(
            "game_started"
        )

        steps = 0

        while (
            not environment.is_terminal()
            and steps < self.config.max_steps
        ):

            state = environment.get_state()
            actions = environment.get_actions()

            action = self.agent.act(
                state,
                actions
            )

            environment.execute_action(action)

            next_state = environment.get_state()
            reward = environment.get_reward()

            experience = Experience(
                state,
                action,
                reward,
                next_state
            )

            self.history.append(experience)

            steps += 1


        final_reward = environment.get_reward()

        self.logger.info(
            "Game run finished after %s steps",
            steps
        )

        self.events.emit(
            "game_finished",
            {
                "steps": steps,
                "reward": final_reward
            }
        )

        self.metrics.record(
            "steps",
            float(steps)
        )

        self.metrics.record(
            "reward",
            final_reward
        )

        return final_reward


    def get_history(self) -> list[Experience]:
        return self.history


    def get_metrics(self) -> Metrics:
        return self.metrics


    def get_events(self) -> EventManager:
        return self.events