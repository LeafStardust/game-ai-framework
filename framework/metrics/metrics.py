class Metrics:
    """
    Stores numerical measurements from agent runs.
    """

    def __init__(self):
        self.data: dict[str, float] = {}


    def record(
        self,
        name: str,
        value: float
    ) -> None:
        self.data[name] = value


    def get(
        self,
        name: str
    ) -> float | None:
        return self.data.get(name)