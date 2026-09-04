"""Exact vanilla ``get_next_tag_key`` for Red/White normal-mode progression.

Tag choice is profile-sensitive: some tags require a discovered center before
``get_current_pool('Tag')`` admits them.  This owner therefore requires an
explicit set of discovered center keys instead of assuming an all-unlocked
profile.  Ineligible slots remain literal ``UNAVAILABLE`` placeholders, matching
vanilla pool indexing and resampling semantics.

Challenge-style banned keys and the debug ``FORCE_TAG`` shortcut are outside the
normal-mode boundary and are intentionally not represented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from games.balatro.env.transition import HeadlessRunState


@dataclass(frozen=True)
class TagMetadata:
    key: str
    min_ante: int | None = None
    requires: str | None = None


# Vanilla P_TAGS order 1..24.  Numeric array position matters because
# pseudorandom_element sorts the dense pool's numeric keys before drawing.
_TAG_METADATA: tuple[TagMetadata, ...] = (
    TagMetadata("tag_uncommon"),
    TagMetadata("tag_rare", requires="j_blueprint"),
    TagMetadata("tag_negative", min_ante=2, requires="e_negative"),
    TagMetadata("tag_foil", requires="e_foil"),
    TagMetadata("tag_holo", requires="e_holo"),
    TagMetadata("tag_polychrome", requires="e_polychrome"),
    TagMetadata("tag_investment"),
    TagMetadata("tag_voucher"),
    TagMetadata("tag_boss"),
    TagMetadata("tag_standard", min_ante=2),
    TagMetadata("tag_charm"),
    TagMetadata("tag_meteor", min_ante=2),
    TagMetadata("tag_buffoon", min_ante=2),
    TagMetadata("tag_handy", min_ante=2),
    TagMetadata("tag_garbage", min_ante=2),
    TagMetadata("tag_ethereal", min_ante=2),
    TagMetadata("tag_coupon"),
    TagMetadata("tag_double"),
    TagMetadata("tag_juggle"),
    TagMetadata("tag_d_six"),
    TagMetadata("tag_top_up", min_ante=2),
    TagMetadata("tag_skip"),
    TagMetadata("tag_orbital", min_ante=2),
    TagMetadata("tag_economy"),
)

ALL_TAG_KEYS = frozenset(meta.key for meta in _TAG_METADATA)
TAG_REQUIREMENT_KEYS = frozenset(
    meta.requires for meta in _TAG_METADATA if meta.requires is not None
)


class TagSelectionError(ValueError):
    """Raised when exact normal Tag selection cannot be performed."""


@dataclass(frozen=True)
class TagProfileState:
    """Profile capability required by vanilla Tag-pool eligibility."""

    discovered_center_keys: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.discovered_center_keys, frozenset):
            raise TagSelectionError("discovered_center_keys must be a frozenset")
        if any(not isinstance(key, str) for key in self.discovered_center_keys):
            raise TagSelectionError(
                "discovered_center_keys must contain only strings"
            )


def _tag_pool(ante: int, profile: TagProfileState) -> list[str]:
    if isinstance(ante, bool) or not isinstance(ante, int):
        raise TagSelectionError("ante must be an exact integer")
    if ante < 1:
        raise TagSelectionError("ante must be at least 1")
    if not isinstance(profile, TagProfileState):
        raise TypeError("profile must be TagProfileState")

    pool: list[str] = []
    available = 0
    for meta in _TAG_METADATA:
        eligible = (
            (meta.requires is None or meta.requires in profile.discovered_center_keys)
            and (meta.min_ante is None or meta.min_ante <= ante)
        )
        if eligible:
            pool.append(meta.key)
            available += 1
        else:
            pool.append("UNAVAILABLE")

    # Vanilla get_current_pool has a Tag fallback when the filtered pool is
    # entirely empty.  Normal P_TAGS always contains unconditional candidates,
    # but preserving the rule documents the source boundary explicitly.
    if available == 0:
        return ["tag_handy"]
    return pool


def select_normal_tag(
    run: "HeadlessRunState",
    profile: TagProfileState,
    *,
    ante: int,
    append: str = "",
) -> tuple["HeadlessRunState", str]:
    """Return one exact normal ``get_next_tag_key`` result and advanced RNG.

    ``get_current_pool('Tag', ..., append)`` produces pool key
    ``'Tag' .. append .. ante``.  If the first indexed slot is ``UNAVAILABLE``,
    vanilla retries against the *same 24-slot pool* using
    ``<pool_key>_resample2``, ``...3``, and so on.  The input run is never
    mutated.
    """
    from games.balatro.env.transition import HeadlessRunState

    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(profile, TagProfileState):
        raise TypeError("profile must be TagProfileState")
    if not isinstance(append, str):
        raise TagSelectionError("append must be a string")

    pool = _tag_pool(ante, profile)
    next_run = run.copy()
    pool_key = f"Tag{append}{ante}"

    index = next_run.rng.pseudorandom_element_index(len(pool), pool_key)
    selected = pool[index]
    resample = 1
    while selected == "UNAVAILABLE":
        resample += 1
        index = next_run.rng.pseudorandom_element_index(
            len(pool),
            f"{pool_key}_resample{resample}",
        )
        selected = pool[index]

    if selected not in ALL_TAG_KEYS:
        raise TagSelectionError("normal Tag selection produced an unknown key")
    return next_run, selected
