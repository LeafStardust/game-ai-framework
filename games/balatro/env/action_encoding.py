"""Versioned fixed action vocabulary and exact legality masking."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Sequence

from games.balatro.env.actions import EnvAction, validate_training_action
from games.balatro.env.observation_encoding import (
    MAX_CONSUMABLES,
    MAX_JOKERS,
    MAX_SHOP_BOOSTERS,
    MAX_SHOP_CONSUMABLES,
    MAX_SHOP_JOKERS,
    MAX_SHOP_VOUCHERS,
)
from games.balatro.env_contract import training_action_contracts


PUBLIC_ACTION_VERSION = "balatro-red-white-public-action-v1"
MAX_PACK_CHOICES = 4


@dataclass(frozen=True)
class ActionSlot:
    index: int
    alias: str
    action_id: str
    params: tuple[tuple[str, int], ...] = ()

    def action(self) -> EnvAction:
        return EnvAction.from_alias(self.alias, dict(self.params))


@dataclass(frozen=True)
class PublicActionSchema:
    version: str
    slots: tuple[ActionSlot, ...]

    @property
    def shape(self) -> tuple[int]:
        return (len(self.slots),)


@dataclass(frozen=True)
class ActionMask:
    schema_version: str
    values: tuple[bool, ...]

    @property
    def shape(self) -> tuple[int]:
        return (len(self.values),)


class PublicActionEncodingError(ValueError):
    """Raised when an action cannot be represented without approximation."""


_PARAMETERIZED_CAPACITIES = {
    "BUY_JOKER": ("slot", MAX_SHOP_JOKERS),
    "BUY_VOUCHER": ("slot", MAX_SHOP_VOUCHERS),
    "BUY_CONSUMABLE": ("slot", MAX_SHOP_CONSUMABLES),
    "OPEN_PACK": ("slot", MAX_SHOP_BOOSTERS),
    "SELL_JOKER": ("joker_index", MAX_JOKERS),
    "CHOOSE_PACK_OPTION": ("option_index", MAX_PACK_CHOICES),
    "USE_CONSUMABLE": ("consumable_index", MAX_CONSUMABLES),
}


def _build_slots() -> tuple[ActionSlot, ...]:
    slots: list[ActionSlot] = []
    for contract in training_action_contracts():
        if contract.action_id is None:
            raise RuntimeError(f"training action {contract.alias} has no canonical action id")
        parameter = _PARAMETERIZED_CAPACITIES.get(contract.alias)
        payloads = ({},) if parameter is None else tuple(
            {parameter[0]: value} for value in range(parameter[1])
        )
        for payload in payloads:
            slots.append(ActionSlot(len(slots), contract.alias, contract.action_id, tuple(payload.items())))
    return tuple(slots)


PUBLIC_ACTION_SCHEMA = PublicActionSchema(PUBLIC_ACTION_VERSION, _build_slots())
_INDEX_BY_ACTION = {slot.action(): slot.index for slot in PUBLIC_ACTION_SCHEMA.slots}


def action_index(action: EnvAction) -> int:
    if not isinstance(action, EnvAction):
        raise TypeError("action must be EnvAction")
    validate_training_action(action)
    try:
        return _INDEX_BY_ACTION[action]
    except KeyError as exc:
        raise PublicActionEncodingError(
            f"action parameters are outside the versioned schema: {action.alias} {action.params!r}"
        ) from exc


def action_from_index(index: int) -> EnvAction:
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("action index must be an integer")
    if index < 0 or index >= len(PUBLIC_ACTION_SCHEMA.slots):
        raise PublicActionEncodingError("action index is outside the versioned schema")
    return PUBLIC_ACTION_SCHEMA.slots[index].action()


def legal_action_mask(legal_actions: Iterable[EnvAction]) -> ActionMask:
    if isinstance(legal_actions, (str, bytes)):
        raise TypeError("legal_actions must be an iterable of EnvAction")
    values = [False] * len(PUBLIC_ACTION_SCHEMA.slots)
    seen: set[int] = set()
    for action in legal_actions:
        index = action_index(action)
        if index in seen:
            raise PublicActionEncodingError(f"duplicate legal action: {action.alias} {action.params!r}")
        seen.add(index)
        values[index] = True
    return ActionMask(PUBLIC_ACTION_VERSION, tuple(values))


def apply_action_mask(probabilities: Sequence[float], mask: ActionMask) -> tuple[float, ...]:
    """Zero illegal mass and normalize legal mass without inventing a fallback."""
    if not isinstance(mask, ActionMask) or mask.schema_version != PUBLIC_ACTION_VERSION:
        raise PublicActionEncodingError("action mask schema version mismatch")
    if len(probabilities) != len(mask.values):
        raise PublicActionEncodingError("probability vector shape does not match action schema")
    numeric: list[float] = []
    for value in probabilities:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PublicActionEncodingError("action probabilities must be numeric")
        number = float(value)
        if not isfinite(number) or number < 0:
            raise PublicActionEncodingError("action probabilities must be finite and nonnegative")
        numeric.append(number)
    masked = [value if allowed else 0.0 for value, allowed in zip(numeric, mask.values)]
    total = sum(masked)
    if total == 0.0:
        if any(mask.values):
            raise PublicActionEncodingError("legal actions have zero probability mass")
        return tuple(masked)
    return tuple(value / total for value in masked)
