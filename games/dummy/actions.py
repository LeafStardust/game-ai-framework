from framework.core.action import Action


class DummyAction(Action):
    """
    Represents an action available in the dummy environment.
    """

    def __init__(self, name):
        self.name = name


INCREASE = DummyAction("INCREASE")
DECREASE = DummyAction("DECREASE")