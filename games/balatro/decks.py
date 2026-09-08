from dataclasses import dataclass


@dataclass(frozen=True)
class BalatroDeck:
    name: str
    starting_money: int = 0
    starting_discards: int = 3
    starting_hand_size: int = 8


BASE_DECK = BalatroDeck(
    name="BASE",
)

RED_DECK = BalatroDeck(
    name="RED",
    starting_discards=4,
)
