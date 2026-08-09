from dataclasses import dataclass
from enum import Enum

from games.balatro.card import BalatroCard


class BalatroEventType(Enum):
    HAND_SCORED = "HAND_SCORED"
    CARDS_DISCARDED = "CARDS_DISCARDED"
    BOOSTER_SKIPPED = "BOOSTER_SKIPPED"
    VOUCHER_SKIPPED = "VOUCHER_SKIPPED"
    ROUND_ENDED = "ROUND_ENDED"
    CARDS_ADDED = "CARDS_ADDED"
    TAROT_USED = "TAROT_USED"
    CARD_SOLD = "CARD_SOLD"
    BOSS_BLIND_DEFEATED = "BOSS_BLIND_DEFEATED"


@dataclass
class BalatroEvent:
    type: BalatroEventType
    cards: list[BalatroCard] | None = None