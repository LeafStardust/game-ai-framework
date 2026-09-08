from framework.core.action import Action


class DummyAction(Action):
    """
    Represents an action available in the dummy environment.
    """

    def __init__(self, name: str):
        self.name: str = name


INCREASE: DummyAction = DummyAction("INCREASE")
DECREASE: DummyAction = DummyAction("DECREASE")