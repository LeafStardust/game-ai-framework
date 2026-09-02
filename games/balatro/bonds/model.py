from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class BondRank(IntEnum):
    # LOCKED means a defining prerequisite is absent. R0 means the Bond is a
    # valid strategic axis for the run but current contribution has not reached
    # its first meaningful development threshold.
    LOCKED = -1
    R0 = 0
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


class MechanicalRole(StrEnum):
    HELD_RANK_PAYOFF = "HELD_RANK_PAYOFF"
    HELD_STATE_PAYOFF = "HELD_STATE_PAYOFF"
    HELD_RETRIGGER = "HELD_RETRIGGER"
    HELD_CARD_XMULT = "HELD_CARD_XMULT"
    PLAYED_RETRIGGER = "PLAYED_RETRIGGER"
    HAND_PAYOFF = "HAND_PAYOFF"
    HAND_LEVEL_ENGINE = "HAND_LEVEL_ENGINE"
    RANK_PAYOFF = "RANK_PAYOFF"
    SUIT_PAYOFF = "SUIT_PAYOFF"
    DENSITY_INFRASTRUCTURE = "DENSITY_INFRASTRUCTURE"
    DECK_THIN_PAYOFF = "DECK_THIN_PAYOFF"
    DECK_THIN_ENGINE = "DECK_THIN_ENGINE"
    DECK_GROWTH_ENGINE = "DECK_GROWTH_ENGINE"
    ECONOMY_PAYOFF = "ECONOMY_PAYOFF"
    ECONOMY_ENGINE = "ECONOMY_ENGINE"
    CONSUMABLE_ENGINE = "CONSUMABLE_ENGINE"
    ENHANCEMENT_PAYOFF = "ENHANCEMENT_PAYOFF"
    ENHANCEMENT_FEED = "ENHANCEMENT_FEED"
    SCALER = "SCALER"
    COPY_ENGINE = "COPY_ENGINE"
    SUPPORT = "SUPPORT"


@dataclass(frozen=True)
class BondContribution:
    source: str
    value: float
    roles: tuple[MechanicalRole, ...] = ()
    targets: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    # Phase C diagnostics. Legacy call sites may omit these while they migrate.
    # source_id identifies one underlying public-state/component source within a
    # Bond evaluation; mechanic records why that source contributes.
    source_id: str | None = None
    mechanic: str | None = None


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
