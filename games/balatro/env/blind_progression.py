"""Exact private blind-progression ownership for R2.9.

Balatro keeps Small/Big/Boss selection status outside the policy-facing card and
score observation. Headless simulation still needs that state to reproduce the
source lifecycle exactly, so this module owns it privately instead of adding
engine-internal blind-status fields to :class:`BalatroState`.

Owned deterministic slices:

* won ``end_round`` progression after the blind has entered ``ROUND_EVAL``;
* the deterministic state mutation of Boss ``cash_out -> reset_blinds()`` once
  an exact next-Boss selection has already been supplied;
* BLIND_SELECT choice after shop exit for an already-valid blind-state set.

Boss-pool selection and post-Boss tag regeneration remain separate R2 RNG owners.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from games.balatro.env.transition import HeadlessRunState


_ALLOWED_STATUSES = frozenset(
    {"Upcoming", "Select", "Current", "Defeated", "Skipped", "Hide"}
)
_ALLOWED_BLINDS = frozenset({"Small", "Big", "Boss"})
_TERMINAL_BLIND_STATUSES = frozenset({"Defeated", "Skipped", "Hide"})


class BlindProgressionError(ValueError):
    """Raised when private blind progression cannot be advanced exactly."""


@dataclass
class BlindProgressionState:
    """Simulator-private mirror of Balatro's blind-selection progression state."""

    small_status: str = "Upcoming"
    big_status: str = "Upcoming"
    boss_status: str = "Upcoming"
    blind_on_deck: str = "Small"
    blind_ante: int = 1
    boss_name: str | None = None
    boss_rerolled: bool = False

    def __post_init__(self) -> None:
        for field_name in ("small_status", "big_status", "boss_status"):
            value = getattr(self, field_name)
            if value not in _ALLOWED_STATUSES:
                raise BlindProgressionError(
                    f"{field_name} must be a canonical blind-state label"
                )
        if self.blind_on_deck not in _ALLOWED_BLINDS:
            raise BlindProgressionError(
                "blind_on_deck must be Small, Big, or Boss"
            )
        if isinstance(self.blind_ante, bool) or not isinstance(self.blind_ante, int):
            raise BlindProgressionError("blind_ante must be an exact integer")
        if self.blind_ante < 1:
            raise BlindProgressionError("blind_ante must be at least 1")
        if self.boss_name is not None and not isinstance(self.boss_name, str):
            raise BlindProgressionError("boss_name must be a string or None")
        if not isinstance(self.boss_rerolled, bool):
            raise BlindProgressionError("boss_rerolled must be a boolean")

    def status_for(self, blind_type: str) -> str:
        normalized = _normalize_blind_type(blind_type)
        return getattr(self, f"{normalized.lower()}_status")

    def set_status(self, blind_type: str, status: str) -> None:
        normalized = _normalize_blind_type(blind_type)
        if status not in _ALLOWED_STATUSES:
            raise BlindProgressionError("invalid canonical blind-state label")
        setattr(self, f"{normalized.lower()}_status", status)


def _normalize_blind_type(blind_type: str) -> str:
    value = str(blind_type).strip().title()
    if value not in _ALLOWED_BLINDS:
        raise BlindProgressionError("blind type must be Small, Big, or Boss")
    return value


def finalize_won_round_progression(
    run: "HeadlessRunState",
    progression: BlindProgressionState,
    *,
    blind_type: str,
) -> tuple["HeadlessRunState", BlindProgressionState]:
    """Apply the exact deterministic blind-state part of vanilla ``end_round``.

    The private progression state is explicit in this primitive's input/output so
    this source-order slice can be validated before it is installed into the
    broader run container. Boss teardown mechanics remain owned separately; this
    owner only records progression that must already have occurred by the time
    ``ROUND_EVAL`` is visible.
    """
    from games.balatro.env.transition import HeadlessRunState

    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")

    state = run.public
    if str(state.phase).upper() != "ROUND_EVAL":
        raise BlindProgressionError(
            "won-round progression requires ROUND_EVAL phase"
        )
    if state.score < state.blind_score:
        raise BlindProgressionError(
            "won-round progression requires the blind target to be met"
        )

    normalized = _normalize_blind_type(blind_type)
    if progression.blind_on_deck != normalized:
        raise BlindProgressionError(
            "blind type does not match private blind_on_deck"
        )
    if progression.status_for(normalized) != "Current":
        raise BlindProgressionError(
            "won-round progression requires current blind status"
        )

    next_run = run.copy()
    next_progression = deepcopy(progression)
    next_progression.set_status(normalized, "Defeated")

    if normalized == "Boss":
        next_run.public.ante += 1
        next_run.round_bonus_hands = 0
        next_run.round_bonus_discards = 0

    return next_run, next_progression


def reset_blinds_after_boss_cashout(
    progression: BlindProgressionState,
    *,
    current_ante: int,
    next_boss_name: str,
) -> BlindProgressionState:
    """Apply vanilla ``reset_blinds()`` after exact next-Boss selection.

    Vanilla reaches this point during Boss cash-out *after* ``end_round`` has
    already advanced Ante. ``cash_out`` records the new Ante as ``blind_ante``;
    ``reset_blinds`` then restores all three statuses to ``Upcoming``, points
    ``blind_on_deck`` at Small, installs the newly selected Boss and clears the
    boss-rerolled flag.

    Tag choices and the RNG/pool logic that chooses ``next_boss_name`` are not
    performed here; callers must supply that result from their exact owners.
    """
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")
    if isinstance(current_ante, bool) or not isinstance(current_ante, int):
        raise BlindProgressionError("current_ante must be an exact integer")
    if current_ante < 2:
        raise BlindProgressionError(
            "Boss reset requires the post-win Ante to be at least 2"
        )
    if not isinstance(next_boss_name, str) or not next_boss_name.strip():
        raise BlindProgressionError("next_boss_name must be a non-empty string")
    if progression.blind_on_deck != "Boss":
        raise BlindProgressionError(
            "reset_blinds requires Boss as private blind_on_deck"
        )
    if progression.boss_status != "Defeated":
        raise BlindProgressionError(
            "reset_blinds requires defeated Boss status"
        )
    if current_ante != progression.blind_ante + 1:
        raise BlindProgressionError(
            "post-Boss current_ante must be exactly one above blind_ante"
        )

    next_progression = deepcopy(progression)
    next_progression.small_status = "Upcoming"
    next_progression.big_status = "Upcoming"
    next_progression.boss_status = "Upcoming"
    next_progression.blind_on_deck = "Small"
    next_progression.blind_ante = current_ante
    next_progression.boss_name = next_boss_name
    next_progression.boss_rerolled = False
    return next_progression


def enter_blind_select_progression(
    progression: BlindProgressionState,
) -> BlindProgressionState:
    """Mirror the deterministic blind choice made by vanilla BLIND_SELECT UI.

    Vanilla chooses Small unless it is Defeated/Skipped/Hide, then Big under the
    same rule, otherwise Boss, and marks the selected blind ``Select``. A
    defeated Boss is special: source ``cash_out`` must call ``reset_blinds()``
    before the next BLIND_SELECT. We reject that stale state rather than silently
    selecting a defeated Boss.
    """
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")
    if "Current" in (
        progression.small_status,
        progression.big_status,
        progression.boss_status,
    ):
        raise BlindProgressionError(
            "BLIND_SELECT cannot begin while a blind is still Current"
        )
    if progression.boss_status == "Defeated":
        raise BlindProgressionError(
            "defeated Boss requires reset_blinds before BLIND_SELECT"
        )

    if progression.small_status not in _TERMINAL_BLIND_STATUSES:
        selected = "Small"
    elif progression.big_status not in _TERMINAL_BLIND_STATUSES:
        selected = "Big"
    else:
        selected = "Boss"

    selected_status = progression.status_for(selected)
    if selected_status not in {"Upcoming", "Select"}:
        raise BlindProgressionError(
            "selected blind is not available for BLIND_SELECT"
        )

    next_progression = deepcopy(progression)
    next_progression.blind_on_deck = selected
    next_progression.set_status(selected, "Select")
    return next_progression
