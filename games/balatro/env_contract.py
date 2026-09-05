"""Versioned RL environment contract for the Balatro Red/White surface.

This module freezes the public action boundary before the headless environment is
implemented. Production ``games.balatro.actions`` identifiers remain canonical;
RL-facing names are aliases only and must not create a second action system.

Only ``SUPPORTED`` entries may be exposed in an initial training action mask.
``PLANNED`` means a production identifier may already exist, but L3 has not yet
frozen a deterministic legality owner for it. ``UNAVAILABLE`` is an explicit
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
REROLL_SHOP_LEGALITY_OWNER = (
    "games.balatro.env.shop_reroll.can_reroll_base_main_shop"
)
REROLL_SHOP_EXECUTION_OWNER = (
    "games.balatro.live.injected.action_dispatcher."
    "LiveMemoryInjectedActionDispatcher.dispatch"
)
SELECT_BLIND_LEGALITY_OWNER = (
    "games.balatro.env.select_blind.can_select_blind_exact"
)
SELECT_BLIND_EXECUTION_OWNER = (
    "games.balatro.live.injected.action_dispatcher."
    "LiveMemoryInjectedActionDispatcher.dispatch"
)
SELL_JOKER_LEGALITY_OWNER = "games.balatro.env.joker_sale.can_sell_joker_exact"
SELL_JOKER_EXECUTION_OWNER = (
    "games.balatro.live.injected.action_dispatcher."
    "LiveMemoryInjectedActionDispatcher.dispatch"
)
SKIP_PACK_LEGALITY_OWNER = "games.balatro.env.pack.can_skip_pack_exact"
SKIP_PACK_EXECUTION_OWNER = (
    "games.balatro.live.injected.action_dispatcher."
    "LiveMemoryInjectedActionDispatcher.dispatch"
)
SKIP_BLIND_LEGALITY_OWNER = "games.balatro.env.skip_blind.can_skip_blind_exact"
SKIP_BLIND_EXECUTION_OWNER = (
    "games.balatro.live.injected.action_dispatcher."
    "LiveMemoryInjectedActionDispatcher.dispatch"
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
# identifiers. Entries remain PLANNED until their deterministic legality owner
# has been audited and frozen. This prevents an aspirational roadmap action from
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
        CapabilityStatus.SUPPORTED,
        REROLL_SHOP_LEGALITY_OWNER,
        REROLL_SHOP_EXECUTION_OWNER,
        "Exact ordinary paid reroll only; free/Tag/bankruptcy cases fail closed.",
    ),
    StrategicActionContract(
        "SELL_JOKER",
        SELL_JOKER,
        CapabilityStatus.SUPPORTED,
        SELL_JOKER_LEGALITY_OWNER,
        SELL_JOKER_EXECUTION_OWNER,
        "Exact active-main-shop sale for audited inventory-only Jokers; other inverse lifecycles fail closed.",
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
        CapabilityStatus.SUPPORTED,
        SKIP_PACK_LEGALITY_OWNER,
        SKIP_PACK_EXECUTION_OWNER,
        "Exact offered-pack skip with explicit SHOP/BLIND_SELECT return origin and Red Card mutation.",
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
        CapabilityStatus.SUPPORTED,
        SKIP_BLIND_LEGALITY_OWNER,
        SKIP_BLIND_EXECUTION_OWNER,
        "Exact Small Blind + Economy Tag subset only; all other Tag and Big-to-Boss outcomes fail closed.",
    ),
    StrategicActionContract(
        "SELECT_BLIND",
        SELECT_BLIND,
        CapabilityStatus.SUPPORTED,
        SELECT_BLIND_LEGALITY_OWNER,
        SELECT_BLIND_EXECUTION_OWNER,
        "Exact audited blind-start dispatch; unsupported tag/inexact state fails closed.",
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