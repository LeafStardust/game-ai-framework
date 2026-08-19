from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Mapping

from games.balatro.strategy import StrategyDefinition
from games.balatro.strategy_tree_catalog import (
    TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES,
)


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _joker_tokens(*names: str) -> frozenset[str]:
    normalized = {_normalize(name) for name in names}
    return frozenset(
        {
            *normalized,
            *(f"{name}joker" for name in normalized if not name.endswith("joker")),
        }
    )


def _without(values: frozenset[str], *names: str) -> frozenset[str]:
    return frozenset(set(values) - set(_joker_tokens(*names)))


def _downgrade_gold_to_silver(
    definition: StrategyDefinition,
    *joker_names: str,
) -> StrategyDefinition:
    """Move modest single-Joker evidence from Gold to Silver.

    Gold is reserved for components strong enough to define/commit a route by
    themselves.  Weak or merely supportive Jokers should raise a strategy without
    causing the tracker to overcommit around one modest pickup.
    """

    tokens = _joker_tokens(*joker_names)
    return replace(
        definition,
        gold_jokers=frozenset(set(definition.gold_jokers) - set(tokens)),
        silver_jokers=frozenset(set(definition.silver_jokers) | set(tokens)),
    )


def guard_unresolved_conditional_relationships(
    definitions: Mapping[str, StrategyDefinition],
) -> Mapping[str, StrategyDefinition]:
    """Keep unresolved/overstated catalogue relationships conservative at runtime."""

    guarded = dict(definitions)

    flush = guarded["flush"]
    guarded["flush"] = replace(
        flush,
        # Seeing Double is Bronze only with compatible mixed/effective-suit
        # structure; owning it alone is not Flush evidence.
        bronze_jokers=_without(flush.bronze_jokers, "Seeing Double"),
    )

    straight_flush = guarded["straight_flush"]
    guarded["straight_flush"] = replace(
        straight_flush,
        # Suit-payoff Jokers require their matching suit shell. DNA is a conflict
        # only when rank-copying has actually collapsed Straight connectivity.
        bronze_jokers=_without(
            straight_flush.bronze_jokers,
            "Arrowhead",
            "Bloodstone",
            "Onyx Agate",
            "Rough Gem",
        ),
        banned_jokers=_without(straight_flush.banned_jokers, "DNA"),
    )

    five_kind = guarded["five_kind"]
    guarded["five_kind"] = replace(
        five_kind,
        # The Idol supports this route only after concentrated rank+suit structure
        # exists; an arbitrary rolled target is not Five-of-a-Kind evidence.
        silver_jokers=_without(five_kind.silver_jokers, "The Idol"),
    )

    flush_five = guarded["flush_five"]
    guarded["flush_five"] = replace(
        flush_five,
        # Flush Five requires identical rank+suit concentration before The Idol is
        # defining evidence.
        gold_jokers=_without(flush_five.gold_jokers, "The Idol"),
    )

    # Weak single-Joker routes should not receive a full Gold (+8) commitment
    # signal from one modest/common pickup.  They remain meaningful Silver (+3)
    # evidence and can still become dominant when reinforced by board/deck context.
    weak_single_joker_cores = {
        "abstract_joker": ("Abstract Joker",),
        "swashbuckler": ("Swashbuckler",),
        "raised_fist": ("Raised Fist",),
        "flower_pot": ("Flower Pot",),
        "cash_cloud_nine": ("Cloud 9",),
        "red_card": ("Red Card",),
        "no_discard_ramen": ("Ramen",),
    }
    for strategy_id, joker_names in weak_single_joker_cores.items():
        guarded[strategy_id] = _downgrade_gold_to_silver(
            guarded[strategy_id],
            *joker_names,
        )

    # Bull and Bootstraps are two cash-scaling payoffs for the exact same economic
    # shell. They should not compete as separate strategy leaves. Keep the legacy
    # node ids topology-compatible but make them permanently non-actionable, then
    # put both defining Jokers on the combined cash scoring leaf.
    retired_cash_requirement = _joker_tokens("__retired_cash_leaf__")
    for strategy_id in ("cash_bull", "cash_bootstraps"):
        legacy = guarded[strategy_id]
        guarded[strategy_id] = replace(
            legacy,
            gold_jokers=frozenset(),
            silver_jokers=frozenset(),
            bronze_jokers=frozenset(),
            required_jokers=retired_cash_requirement,
            entry_evidence_cap=0.0,
        )

    cash_scoring = guarded["cash_bull_bootstraps"]
    guarded["cash_bull_bootstraps"] = replace(
        cash_scoring,
        gold_jokers=_joker_tokens("Bull", "Bootstraps"),
    )

    return MappingProxyType(guarded)


RUNTIME_UNIVERSAL_BALATRO_STRATEGIES = guard_unresolved_conditional_relationships(
    TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES
)
