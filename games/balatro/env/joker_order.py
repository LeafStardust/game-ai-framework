"""Simulator-private Joker ordering for Amber Acorn and order-sensitive scoring.

Balatro's Amber Acorn does not shuffle from the currently displayed Joker order.
Each ``G.jokers:shuffle('aajk')`` call reaches ``pseudoshuffle``, which first
sorts by each Joker card's monotonic engine ``sort_id``.  Live observation already
carries that value as ``joker.live_id``.

This module owns only the hidden ordering facts needed by the simulator.  It does
not expose Amber Acorn, flip Jokers, or alter policy observations yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


class JokerOrderError(ValueError):
    """Raised when exact Joker creation/physical order cannot be maintained."""


def _same_objects(left: Sequence[Any], right: Sequence[Any]) -> bool:
    return len(left) == len(right) and {id(value) for value in left} == {
        id(value) for value in right
    }


def derive_joker_creation_order(jokers: Sequence[Any]) -> list[Any] | None:
    """Recover exact relative Joker ``sort_id`` order when public state proves it.

    Empty and single-Joker areas are intrinsically ordered.  Multi-Joker live
    states require a unique exact integer ``live_id`` on every Joker.  Mixed,
    missing, boolean, noninteger, or duplicate ids fail closed.
    """
    if not isinstance(jokers, Sequence) or isinstance(jokers, (str, bytes)):
        raise TypeError("jokers must be a sequence")

    values = list(jokers)
    if len(values) <= 1:
        return values

    live_ids = [getattr(joker, "live_id", None) for joker in values]
    if not all(type(value) is int for value in live_ids):
        return None
    if len(set(live_ids)) != len(live_ids):
        return None
    return sorted(values, key=lambda joker: joker.live_id)


@dataclass
class JokerOrderState:
    """Exact hidden Joker creation order plus current physical area order.

    ``creation_order`` is the source order restored by ``pseudoshuffle`` before
    every Amber shuffle. ``physical_order`` is the actual order used for
    order-sensitive Joker evaluation. Both lists contain the same Joker objects as
    the canonical owned-Joker list; this owner never clones or invents Jokers.
    """

    creation_order: list[Any]
    physical_order: list[Any]

    @classmethod
    def from_public(cls, jokers: Sequence[Any]) -> "JokerOrderState | None":
        creation = derive_joker_creation_order(jokers)
        if creation is None:
            return None
        physical = list(jokers)
        return cls(creation_order=creation, physical_order=physical)

    def validate_against(self, jokers: Sequence[Any]) -> None:
        values = list(jokers)
        if not _same_objects(self.creation_order, values):
            raise JokerOrderError("Joker creation order is stale relative to owned Jokers")
        if not _same_objects(self.physical_order, values):
            raise JokerOrderError("Joker physical order is stale relative to owned Jokers")

        if len(self.creation_order) > 1:
            live_ids = [getattr(joker, "live_id", None) for joker in self.creation_order]
            known_ids = all(type(value) is int for value in live_ids)
            if known_ids:
                if len(set(live_ids)) != len(live_ids):
                    raise JokerOrderError("Joker creation ids must be unique")
                if self.creation_order != sorted(
                    self.creation_order,
                    key=lambda joker: joker.live_id,
                ):
                    raise JokerOrderError("Joker creation order is not sort_id order")

    def acquire(self, joker: Any, owned_jokers: Sequence[Any]) -> None:
        """Append one newly created Joker to exact creation and physical order."""
        before = list(owned_jokers)
        if joker in before:
            raise JokerOrderError("newly acquired Joker is already owned")
        self.validate_against(before)
        self.creation_order.append(joker)
        self.physical_order.append(joker)

    def remove(self, joker: Any, owned_jokers: Sequence[Any]) -> None:
        """Remove one known Joker from both hidden orders before public removal."""
        before = list(owned_jokers)
        self.validate_against(before)
        if joker not in before:
            raise JokerOrderError("sold Joker is not owned")
        self.creation_order.remove(joker)
        self.physical_order.remove(joker)

    def set_physical_order(self, order: Sequence[Any], owned_jokers: Sequence[Any]) -> None:
        """Install a proven hidden permutation without changing creation order."""
        values = list(owned_jokers)
        self.validate_against(values)
        candidate = list(order)
        if not _same_objects(candidate, values):
            raise JokerOrderError("physical Joker order must be an exact owned-Joker permutation")
        self.physical_order = candidate
