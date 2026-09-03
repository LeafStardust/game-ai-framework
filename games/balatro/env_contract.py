"""Versioned RL environment contract for the Balatro Red/White surface.

This module freezes the public action boundary before the headless environment is
implemented.  Production ``games.balatro.actions`` identifiers remain canonical;
RL-facing names are aliases only and must not create a second action system.

Only ``SUPPORTED`` entries may be exposed in an initial training action mask.
``PLANNED`` means a production identifier may already exist, but L3 has not yet
frozen a deterministic legality owner for it.  ``UNAVAILABLE`` is an explicit
capability exclusion and must never receive phantom value during training.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    SELECT_BLIND,
    SELECT_PACK_CARD,
    SELL_JOKER,
    SKIP_BLIND,
    SKIP_BOOSTER,
    USE_CONSUMABLE,
)


BALATRO_ENV_CONTRACT_VERSION = "l3-v1"

SHOP_LEGALITY_OWNER = (
    "games.balatro.live.shop.BalatroShopActionGenerator.generate_actions"
)
LIVE_EXECUTION_OWNER = (
    "games.balatro.live.interfaces.BalatroActionExecutor.command_for"
)


class CapabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PLANNED = "PLANNED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class StrategicActionContract:
    """One stable RL alias and its canonical production action ownership."""

    alias: str
    action_id: str | None
    status: CapabilityStatus
    legality_owner: str | None = None
    execution_owner: str | None = None
    note: str = ""

    @property
    def training_exposed(self) -> bool:
        return self.status is CapabilityStatus.SUPPORTED


# The Phase-R vocabulary is represented here without changing production action
# identifiers.  Entries remain PLANNED until their deterministic legality owner
# has been audited and frozen.  This prevents an aspirational roadmap action from
# leaking into a training mask before live/simulator parity exists.
STRATEGIC_ACTION_CONTRACTS: tuple[StrategicActionContract, ...] = (
    StrategicActionContract(
        "END_SHOP",
        END_SHOP,
        CapabilityStatus.SUPPORTED,
        SHOP_LEGALITY_OWNER,
        LIVE_EXECUTION_OWNER,
    ),
    StrategicActionContract(
        "BUY_JOKER",
        BUY_JOKER,
        CapabilityStatus.SUPPORTED,
        SHOP_LEGALITY_OWNER,
        LIVE_EXECUTION_OWNER,
    ),
    StrategicActionContract(
        "BUY_VOUCHER",
        BUY_VOUCHER,
        CapabilityStatus.SUPPORTED,
        SHOP_LEGALITY_OWNER,
        LIVE_EXECUTION_OWNER,
    ),
    StrategicActionContract(
        "BUY_CONSUMABLE",
        BUY_CONSUMABLE,
        CapabilityStatus.SUPPORTED,
        SHOP_LEGALITY_OWNER,
        LIVE_EXECUTION_OWNER,
    ),
    StrategicActionContract(
        "OPEN_PACK",
        BUY_BOOSTER,
        CapabilityStatus.SUPPORTED,
        SHOP_LEGALITY_OWNER,
        LIVE_EXECUTION_OWNER,
        "Production BUY_BOOSTER purchases and enters the selected booster pack.",
    ),
    StrategicActionContract(
        "REROLL_SHOP",
        REFRESH_SHOP,
        CapabilityStatus.PLANNED,
        note="Canonical production action exists; deterministic legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "SELL_JOKER",
        SELL_JOKER,
        CapabilityStatus.PLANNED,
        note="Canonical production action exists; deterministic legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "BUY_CARD",
        None,
        CapabilityStatus.PLANNED,
        note="No dedicated canonical BUY_CARD production identifier exists yet.",
    ),
    StrategicActionContract(
        "CHOOSE_PACK_OPTION",
        SELECT_PACK_CARD,
        CapabilityStatus.PLANNED,
        note="Canonical production action exists; deterministic legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "SKIP_PACK",
        SKIP_BOOSTER,
        CapabilityStatus.PLANNED,
        note="Canonical production action exists; deterministic legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "USE_CONSUMABLE",
        USE_CONSUMABLE,
        CapabilityStatus.PLANNED,
        note="Canonical production action exists; deterministic legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "SKIP_BLIND",
        SKIP_BLIND,
        CapabilityStatus.PLANNED,
        note="Canonical production action exists; deterministic legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "SELECT_BLIND",
        SELECT_BLIND,
        CapabilityStatus.PLANNED,
        note="SELECT_BLIND is the production start/select-blind action; legality owner is not frozen yet.",
    ),
    StrategicActionContract(
        "REROLL_BOSS",
        None,
        CapabilityStatus.UNAVAILABLE,
        note="No canonical production action/owner is available in the frozen Red/White surface.",
    ),
)


def training_action_contracts() -> tuple[StrategicActionContract, ...]:
    """Return only actions currently safe to expose to an RL legality mask."""

    return tuple(
        contract
        for contract in STRATEGIC_ACTION_CONTRACTS
        if contract.training_exposed
    )


def contract_for(alias: str) -> StrategicActionContract:
    """Return the unique contract for an RL-facing strategic action alias."""

    normalized = str(alias).upper()
    for contract in STRATEGIC_ACTION_CONTRACTS:
        if contract.alias == normalized:
            return contract
    raise KeyError(normalized)


def validate_env_contract() -> None:
    """Fail closed if the frozen contract can expose an ownerless action."""

    aliases = [contract.alias for contract in STRATEGIC_ACTION_CONTRACTS]
    if len(aliases) != len(set(aliases)):
        raise ValueError("Balatro environment contract contains duplicate aliases")

    for contract in training_action_contracts():
        if not contract.action_id:
            raise ValueError(f"training action {contract.alias} has no canonical action id")
        if not contract.legality_owner:
            raise ValueError(f"training action {contract.alias} has no legality owner")
        if not contract.execution_owner:
            raise ValueError(f"training action {contract.alias} has no execution owner")


validate_env_contract()
