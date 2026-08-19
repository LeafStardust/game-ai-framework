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
    """Move supportive evidence from Gold to Silver.

    Gold is reserved for components strong enough to make a strategy viable and
    unusually effective by themselves. Supportive or merely direction-setting
    Jokers should raise a route without manufacturing a commitment signal.
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

    # Gold means a Joker can make the route genuinely viable/strong on its own.
    # These are useful support/direction pieces, but not sufficient for +8 evidence.
    weak_single_joker_cores = {
        "abstract_joker": ("Abstract Joker",),
        "swashbuckler": ("Swashbuckler",),
        "raised_fist": ("Raised Fist",),
        "flower_pot": ("Flower Pot",),
        "cash_cloud_nine": ("Cloud 9",),
        "red_card": ("Red Card",),
        "no_discard_ramen": ("Ramen",),
        "no_discard_reserve": ("Banner", "Delayed Gratification"),
        "last_hand_acrobat": ("Acrobat",),
        # Hand/economy enablers are useful but do not by themselves make the route
        # powerful enough to deserve a Gold commitment signal.
        "straight": ("Shortcut", "Four Fingers", "Superposition"),
        "face_held_economy": ("Reserved Parking",),
        "face_business_card": ("Business Card",),
        "faceless_discard_economy": ("Faceless Joker",),
        "faceless_ride_bus": ("Ride the Bus",),
        "sixes": ("Sixth Sense",),
        "queens_shoot_moon": ("Shoot the Moon",),
        "hiker_training": ("Hiker",),
        "planet_satellite": ("Satellite",),
        "discard_mail_rebate": ("Mail-In Rebate",),
        "loyalty_cycle": ("Loyalty Card",),
        # Run-log calibration: these generator/scaler pieces repeatedly produced
        # an immediate Gold ~=8 dominant strategy before the rest of the route
        # existed. They should create direction, not commitment, by themselves.
        "tarot_engine": ("Fortune Teller",),
        "tarot_cartomancer": ("Cartomancer",),
        "tarot_hallucination": ("Hallucination",),
        "tarot_eight_ball": ("8 Ball", "Eight Ball"),
    }
    for strategy_id, joker_names in weak_single_joker_cores.items():
        guarded[strategy_id] = _downgrade_gold_to_silver(
            guarded[strategy_id],
            *joker_names,
        )

    # PhotoChad is a combo route, not a Photograph-only route. The logs showed
    # Photograph alone creating an ~8-point highlighted leaf for long stretches.
    # Require both positive components in the leaf and make each Silver: one piece
    # is exploratory evidence; the pair is a meaningful ~6-point build direction.
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
