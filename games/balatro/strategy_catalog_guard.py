from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Mapping

from games.balatro.strategy import StrategyDefinition
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES


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

    return MappingProxyType(guarded)


RUNTIME_UNIVERSAL_BALATRO_STRATEGIES = guard_unresolved_conditional_relationships(
    UNIVERSAL_BALATRO_STRATEGIES
)
