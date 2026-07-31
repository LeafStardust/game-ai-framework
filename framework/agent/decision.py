from abc import ABC, abstractmethod


class DecisionEngine(ABC):
    """
    Defines how an agent selects an action.
    """

    @abstractmethod
    def choose_action(self, state, actions):
        pass