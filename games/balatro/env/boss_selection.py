"""Exact vanilla Boss-pool selection for Red/White normal-mode R2 progression.

This module owns the source ``get_new_boss()`` path after prescribed/forced-Boss
shortcuts are excluded.  Vanilla builds an eligible keyed table, removes banned
keys, keeps only Bosses with the minimum historical use count, then calls
``pseudorandom_element(..., pseudoseed('boss'))``.  Because the keyed table has
no ``sort_id`` values, ``pseudorandom_element`` sorts the surviving Boss keys
lexicographically before one inclusive LuaJIT integer draw.

Boss selection state is simulator-private.  It must not be reconstructed from
which Bosses happened to appear in policy-visible observations.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from games.balatro.env.transition import HeadlessRunState


@dataclass(frozen=True)
class BossMetadata:
    key: str
    name: str
    min_ante: int
    showdown: bool = False


# Pinned to vanilla ``G.P_BLINDS`` at the repository's source-audit commit.
# ``boss.max`` is intentionally absent: vanilla ``get_new_boss`` does not consult
# it.  Showdown selection is controlled only by ``showdown`` + ``win_ante``.
_BOSS_METADATA: tuple[BossMetadata, ...] = (
    BossMetadata("bl_arm", "The Arm", 2),
    BossMetadata("bl_club", "The Club", 1),
    BossMetadata("bl_eye", "The Eye", 3),
    BossMetadata("bl_final_acorn", "Amber Acorn", 10, True),
    BossMetadata("bl_final_bell", "Cerulean Bell", 10, True),
    BossMetadata("bl_final_heart", "Crimson Heart", 10, True),
    BossMetadata("bl_final_leaf", "Verdant Leaf", 10, True),
    BossMetadata("bl_final_vessel", "Violet Vessel", 10, True),
    BossMetadata("bl_fish", "The Fish", 2),
    BossMetadata("bl_flint", "The Flint", 2),
    BossMetadata("bl_goad", "The Goad", 1),
    BossMetadata("bl_head", "The Head", 1),
    BossMetadata("bl_hook", "The Hook", 1),
    BossMetadata("bl_house", "The House", 2),
    BossMetadata("bl_manacle", "The Manacle", 1),
    BossMetadata("bl_mark", "The Mark", 2),
    BossMetadata("bl_mouth", "The Mouth", 2),
    BossMetadata("bl_needle", "The Needle", 2),
    BossMetadata("bl_ox", "The Ox", 6),
    BossMetadata("bl_pillar", "The Pillar", 1),
    BossMetadata("bl_plant", "The Plant", 4),
    BossMetadata("bl_psychic", "The Psychic", 1),
    BossMetadata("bl_serpent", "The Serpent", 5),
    BossMetadata("bl_tooth", "The Tooth", 3),
    BossMetadata("bl_wall", "The Wall", 2),
    BossMetadata("bl_water", "The Water", 2),
    BossMetadata("bl_wheel", "The Wheel", 2),
    BossMetadata("bl_window", "The Window", 1),
)

BOSS_METADATA_BY_KEY = {meta.key: meta for meta in _BOSS_METADATA}
BOSS_KEY_BY_NAME = {meta.name: meta.key for meta in _BOSS_METADATA}
ALL_BOSS_KEYS = frozenset(BOSS_METADATA_BY_KEY)


class BossSelectionError(ValueError):
    """Raised when exact vanilla Boss selection cannot be performed."""


def _fresh_usage_counts() -> dict[str, int]:
    # Vanilla ``Game:init_game_object`` initializes every ``G.P_BLINDS`` Boss to
    # zero, including showdown Bosses.
    return {key: 0 for key in sorted(ALL_BOSS_KEYS)}


@dataclass
class BossSelectionState:
    """Simulator-private state consumed by vanilla ``get_new_boss``."""

    usage_counts: dict[str, int] = field(default_factory=_fresh_usage_counts)
    banned_keys: frozenset[str] = field(default_factory=frozenset)
    win_ante: int = 8

    def __post_init__(self) -> None:
        if not isinstance(self.usage_counts, dict):
            raise BossSelectionError("usage_counts must be a dictionary")
        if set(self.usage_counts) != ALL_BOSS_KEYS:
            raise BossSelectionError(
                "usage_counts must contain every vanilla Boss key exactly once"
            )
        for key, value in self.usage_counts.items():
            if not isinstance(key, str):
                raise BossSelectionError("Boss usage keys must be strings")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BossSelectionError(
                    "Boss usage counts must be exact nonnegative integers"
                )
        if not isinstance(self.banned_keys, frozenset):
            raise BossSelectionError("banned_keys must be a frozenset")
        if any(not isinstance(key, str) for key in self.banned_keys):
            raise BossSelectionError("banned_keys must contain only strings")
        if isinstance(self.win_ante, bool) or not isinstance(self.win_ante, int):
            raise BossSelectionError("win_ante must be an exact integer")
        if self.win_ante <= 0:
            raise BossSelectionError("win_ante must be positive")


@dataclass(frozen=True)
class BossSelectionResult:
    boss_key: str
    boss_name: str


def _eligible_keys(state: BossSelectionState, ante: int) -> list[str]:
    # Vanilla deliberately clamps only the ordinary-Boss minimum-Ante test to 1.
    # The literal Ante is still used by the showdown tests, so Hieroglyph /
    # Petroglyph Ante 0 and negative values must reach this function unchanged.
    effective_ante = max(1, ante)
    eligible: list[str] = []
    for meta in _BOSS_METADATA:
        if meta.key in state.banned_keys:
            continue
        if not meta.showdown:
            if (
                meta.min_ante <= effective_ante
                and (effective_ante % state.win_ante != 0 or ante < 2)
            ):
                eligible.append(meta.key)
        elif ante % state.win_ante == 0 and ante >= 2:
            eligible.append(meta.key)

    if not eligible:
        raise BossSelectionError("Boss pool has no eligible Bosses")

    minimum_use = min(state.usage_counts[key] for key in eligible)
    # Vanilla ``pseudorandom_element`` sorts string table keys before drawing.
    return sorted(
        key for key in eligible if state.usage_counts[key] == minimum_use
    )


def select_normal_boss(
    run: "HeadlessRunState",
    selection_state: BossSelectionState,
    *,
    ante: int,
) -> tuple["HeadlessRunState", BossSelectionState, BossSelectionResult]:
    """Select one exact Boss through vanilla's normal ``get_new_boss`` path.

    Prescribed Bosses and the global debug ``FORCE_BOSS`` shortcut are outside
    Red/White normal-mode ownership and are intentionally not represented here.
    The input run/RNG and usage state are never mutated.
    """
    from games.balatro.env.transition import HeadlessRunState

    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(selection_state, BossSelectionState):
        raise TypeError("selection_state must be BossSelectionState")
    if isinstance(ante, bool) or not isinstance(ante, int):
        raise BossSelectionError("ante must be an exact integer")

    candidates = _eligible_keys(selection_state, ante)
    next_run = run.copy()
    next_selection = deepcopy(selection_state)
    index = next_run.rng.pseudorandom_element_index(len(candidates), "boss")
    boss_key = candidates[index]
    next_selection.usage_counts[boss_key] += 1
    metadata = BOSS_METADATA_BY_KEY[boss_key]
    return (
        next_run,
        next_selection,
        BossSelectionResult(boss_key=boss_key, boss_name=metadata.name),
    )