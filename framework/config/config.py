class FrameworkConfig:
    """
    Stores framework-level configuration settings.
    """

    def __init__(
        self,
        max_steps: int = 1000,
        seed: int | None = None,
        policy: str = "greedy",
        temperature: float = 1.0
    ):
        self.max_steps: int = max_steps
        self.seed: int | None = seed

        self.policy: str = policy
        self.temperature: float = temperature