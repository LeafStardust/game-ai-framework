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
    """Move supportive evidence to Silver and keep tier membership exclusive."""

    tokens = _joker_tokens(*joker_names)
    return replace(
        definition,
        gold_jokers=frozenset(set(definition.gold_jokers) - set(tokens)),
        silver_jokers=frozenset(set(definition.silver_jokers) | set(tokens)),
        bronze_jokers=frozenset(set(definition.bronze_jokers) - set(tokens)),
    )


def _retire_standalone_strategy(definition: StrategyDefinition) -> StrategyDefinition:
    """Keep a topology/catalog ID but remove it from active strategy competition."""

    return replace(
        definition,
        gold_jokers=frozenset(),
        silver_jokers=frozenset(),
        bronze_jokers=frozenset(),
        gold_consumables=frozenset(),
        silver_consumables=frozenset(),
        bronze_consumables=frozenset(),
        gold_planets=frozenset(),
        silver_planets=frozenset(),
        bronze_planets=frozenset(),
        gold_vouchers=frozenset(),
        silver_vouchers=frozenset(),
        bronze_vouchers=frozenset(),
        required_jokers=_joker_tokens("__retired_non_standalone_strategy__"),
        minimum_positive_jokers=0,
        entry_evidence_cap=0.0,
    )


def guard_unresolved_conditional_relationships(
    definitions: Mapping[str, StrategyDefinition],
) -> Mapping[str, StrategyDefinition]:
    """Keep unresolved/overstated catalogue relationships conservative at runtime."""

    guarded = dict(definitions)

    flush = guarded["flush"]
    guarded["flush"] = replace(
        flush,
        bronze_jokers=_without(flush.bronze_jokers, "Seeing Double"),
    )

    straight_flush = guarded["straight_flush"]
    guarded["straight_flush"] = replace(
        straight_flush,
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
        silver_jokers=_without(five_kind.silver_jokers, "The Idol"),
    )

    flush_five = guarded["flush_five"]
    guarded["flush_five"] = replace(
        flush_five,
        gold_jokers=_without(flush_five.gold_jokers, "The Idol"),
    )

    weak_single_joker_cores = {
        "swashbuckler": ("Swashbuckler",),
        "flower_pot": ("Flower Pot",),
        "red_card": ("Red Card",),
        "no_discard_ramen": ("Ramen",),
        "last_hand_acrobat": ("Acrobat",),
        "no_discard_green": ("Green Joker",),
        "straight": ("Shortcut", "Four Fingers"),
        "sixes": ("Sixth Sense",),
        "queens_shoot_moon": ("Shoot the Moon",),
        "hiker_training": ("Hiker",),
        "loyalty_cycle": ("Loyalty Card",),
        "tarot_engine": ("Fortune Teller",),
        "tarot_cartomancer": ("Cartomancer",),
        "tarot_hallucination": ("Hallucination",),
        "tarot_eight_ball": ("8 Ball", "Eight Ball"),
        "joker_stencil": ("Joker Stencil",),
    }
    for strategy_id, joker_names in weak_single_joker_cores.items():
        guarded[strategy_id] = _downgrade_gold_to_silver(
            guarded[strategy_id],
            *joker_names,
        )

    # Support/economy mechanisms do not compete as standalone routes. Cash-producing
    # components are rehomed conditionally under Bull/Bootstraps by the state-aware
    # cash-scoring support policy; they cannot activate that scoring route alone.
    non_standalone_strategy_ids = frozenset(
        {
            "abstract_joker",
            "raised_fist",
            "face_held_economy",
            "face_business_card",
            "faceless_discard_economy",
            "planet_satellite",
            "cash_hoard",
            "cash_growth",
            "cash_cloud_nine",
            "discard_mail_rebate",
            "no_discard_reserve",
        }
    )
    for strategy_id in non_standalone_strategy_ids:
        guarded[strategy_id] = _retire_standalone_strategy(guarded[strategy_id])

    # Superposition is only weak support for Straight: keep it Bronze rather than
    # allowing it to manufacture a Silver commitment signal.
    straight = guarded["straight"]
    superposition = _joker_tokens("Superposition")
    guarded["straight"] = replace(
        straight,
        gold_jokers=frozenset(set(straight.gold_jokers) - set(superposition)),
        silver_jokers=frozenset(set(straight.silver_jokers) - set(superposition)),
        bronze_jokers=frozenset(set(straight.bronze_jokers) | set(superposition)),
    )

    photochad = guarded["face_photochad"]
    guarded["face_photochad"] = replace(
        photochad,
        gold_jokers=_without(photochad.gold_jokers, "Photograph"),
        silver_jokers=frozenset(
            set(photochad.silver_jokers)
            | set(_joker_tokens("Photograph", "Hanging Chad"))
        ),
        minimum_positive_jokers=2,
    )

    # Bull and Bootstraps are the defining cash-to-score cores. Their old individual
    # leaves stay retired so there is one cash-scoring index. Either core can activate
    # the combined route; owning both strengthens it further through conditional rules.
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
