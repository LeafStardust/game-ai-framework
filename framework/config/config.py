class FrameworkConfig:
    """
    Stores framework-level configuration settings.
    """

    def __init__(
        self,
        max_steps: int = 1000,
        seed: int | None = None
    ):
        self.max_steps: int = max_steps
        self.seed: int | None = seed