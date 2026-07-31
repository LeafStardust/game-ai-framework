from abc import ABC, abstractmethod


class Evaluator(ABC):
    """
    Defines how states or actions are evaluated.
    """

    @abstractmethod
    def evaluate(self, state, action):
        pass