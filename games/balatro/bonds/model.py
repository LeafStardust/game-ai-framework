from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class BondRank(IntEnum):
    LOCKED = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5


class BondRealization(StrEnum):
    DORMANT = "DORMANT"
    PARTIAL = "PARTIAL"
    ACTIVE = "ACTIVE"
    MATURE = "MATURE"


@dataclass(frozen=True)
class BondContribution:
    source: str
    value: float


@dataclass(frozen=True)
class BondDevelopment:
    bond_id: str
    unlocked: bool
    contribution: float
    rank: BondRank
    next_rank_threshold: float | None
    contributions: tuple[BondContribution, ...]
    target: str | None = None
    realization: BondRealization = BondRealization.DORMANT

    @property
    def points_to_next_rank(self) -> float | None:
        if self.next_rank_threshold is None:
            return None
        return max(0.0, self.next_rank_threshold - self.contribution)
