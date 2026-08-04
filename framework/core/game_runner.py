from framework.agent.agent import Agent
from framework.core.environment import GameEnvironment
from framework.core.experience import Experience
from framework.config.config import FrameworkConfig
from framework.logging.logger import get_logger


class GameRunner:
    """
    Handles the execution loop between an agent and an environment.
    """

    def __init__(
        self,
        environment: GameEnvironment,
        agent: Agent,
        config: FrameworkConfig | None = None
    ):
        self.environment: GameEnvironment = environment
        self.agent: Agent = agent
        self.config: FrameworkConfig = config or FrameworkConfig()
        self.history: list[Experience] = []
        self.logger = get_logger(__name__)


    def run(self) -> float:

        self.environment.reset()
        self.logger.info("Game run started")

        steps = 0

        while (
            not self.environment.is_terminal()
            and steps < self.config.max_steps
        ):

            state = self.environment.get_state()
            actions = self.environment.get_actions()

            action = self.agent.act(
                state,
                actions
            )

            self.environment.execute_action(action)

            next_state = self.environment.get_state()
            reward = self.environment.get_reward()

            experience = Experience(
                state,
                action,
                reward,
                next_state
            )

            self.history.append(experience)

            steps += 1

        self.logger.info(
            "Game run finished after %s steps",
            steps
        )

        return self.environment.get_reward()


    def get_history(self) -> list[Experience]:
        return self.history