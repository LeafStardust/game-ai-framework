from abc import ABC, abstractmethod


class GameEnvironment(ABC):
    """
    Interface between the AI agent and a game.
    """

    @abstractmethod
    def reset(self):
        pass


    @abstractmethod
    def get_state(self):
        pass


    @abstractmethod
    def get_actions(self):
        pass


    @abstractmethod
    def execute_action(self, action):
        pass


    @abstractmethod
    def is_terminal(self):
        pass


    @abstractmethod
    def get_reward(self):
        pass