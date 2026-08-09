from dataclasses import dataclass


@dataclass
class BalatroCard:
    """
    Represents a Balatro playing card.
    """

    rank: str
    suit: str
    enhancement: str | None = None