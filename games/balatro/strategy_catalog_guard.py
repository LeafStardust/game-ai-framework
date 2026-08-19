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


def guard_unresolved_conditional_relationships(
    definitions: Mapping[str, StrategyDefinition],
) -> Mapping[str, StrategyDefinition]:
    """Keep unresolved parenthetical catalogue rules Neutral at runtime.

    The concrete strategy documents deliberately distinguish unconditional evidence
    from parenthetical, state-dependent relationships. Until those public-state
    predicates are encoded, flattening a conditional relationship into the static
    Gold/Silver/Bronze/Banned buckets creates false strategy evidence. This guard
    removes only relationships that are currently flattened incorrectly; entries
    already omitted from the static catalogue remain untouched.

    This is intentionally conservative and temporary. A later 1.0F catalogue slice
    should replace each guarded Neutral relationship with an explicit public-state
    condition rather than restoring it unconditionally.
    """

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

    # Bull and Bootstraps are two cash-scaling payoffs for the exact same economic
    # shell. They should not compete as separate strategy leaves. Keep the legacy
    # node ids topology-compatible but make them permanently non-actionable, then
    # put both defining Jokers on the combined cash scoring leaf. Conditional
    # support that still references the retired ids is capped to zero by the
    # impossible defining requirement, so only cash_bull_bootstraps can surface.
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
