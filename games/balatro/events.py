from dataclasses import dataclass
from enum import Enum

from games.balatro.card import BalatroCard


class BalatroEventType(Enum):
    HAND_SCORED = "HAND_SCORED"
    CARDS_DISCARDED = "CARDS_DISCARDED"
    BOOSTER_SKIPPED = "BOOSTER_SKIPPED"
    VOUCHER_SKIPPED = "VOUCHER_SKIPPED"
    ROUND_ENDED = "ROUND_ENDED"


@dataclass
class BalatroEvent:
    type: BalatroEventType
    cards: list[BalatroCard] | None = None