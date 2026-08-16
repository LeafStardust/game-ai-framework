from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, ClassVar, Mapping

from framework.core.state import GameState

from games.balatro.card import BalatroCard
from games.balatro.events import BalatroEvent
from games.balatro.hand import PokerHand

if TYPE_CHECKING:
    from games.balatro.scoring import HandScore


class Playstyle(str, Enum):
    """Composable Balatro build directions used by Joker affinity metadata.

    These are independent axes rather than mutually-exclusive archetypes. A build
    can therefore support combinations such as FULL_HOUSE + NO_FACE_CARDS or
    FLUSH + DIAMONDS without requiring pairwise Joker synergy tables.
    """

    HIGH_CARD = "HIGH_CARD"
    PAIR = "PAIR"
    TWO_PAIR = "TWO_PAIR"
    THREE_OF_A_KIND = "THREE_OF_A_KIND"
    STRAIGHT = "STRAIGHT"
    FLUSH = "FLUSH"
    FULL_HOUSE = "FULL_HOUSE"
    FOUR_OF_A_KIND = "FOUR_OF_A_KIND"
    FIVE_OF_A_KIND = "FIVE_OF_A_KIND"
    FLUSH_HOUSE = "FLUSH_HOUSE"
    FLUSH_FIVE = "FLUSH_FIVE"

    FACE_CARDS = "FACE_CARDS"
    NO_FACE_CARDS = "NO_FACE_CARDS"

    SPADES = "SPADES"
    HEARTS = "HEARTS"
    CLUBS = "CLUBS"
    DIAMONDS = "DIAMONDS"

    HELD_CARDS = "HELD_CARDS"
    DISCARD = "DISCARD"
    NO_DISCARD = "NO_DISCARD"
    ECONOMY = "ECONOMY"
    CONSUMABLES = "CONSUMABLES"


class PlaystyleAffinity(IntEnum):
    """Directional Joker relationship to one playstyle axis.

    Neutral is deliberately represented by an omitted mapping entry. Keeping only
    POSITIVE/NEGATIVE declarations prevents a meaningless sea of explicit neutral
    metadata across the Joker catalogue.
    """

    NEGATIVE = -1
    POSITIVE = 1


@dataclass
class JokerContext:

    state: GameState
    score: HandScore | None = None
    poker_hand: PokerHand | None = None

    cards: list[BalatroCard] = field(default_factory=list)
    held_cards: list[BalatroCard] = field(default_factory=list)

    trigger: str = ""
    event: BalatroEvent | None = None
    data: dict = field(default_factory=dict)


class Joker(ABC):
    """Base Joker model plus declarative build-direction metadata."""

    playstyle_affinities: ClassVar[
        Mapping[Playstyle, PlaystyleAffinity]
    ] = {}

    def playstyle_affinity(
        self,
        playstyle: Playstyle,
    ) -> PlaystyleAffinity | None:
        """Return this Joker's declared relation, or ``None`` for neutral."""

        return self.playstyle_affinities.get(playstyle)

    @abstractmethod
    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:
        pass
