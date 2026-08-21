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


def _downgrade_to_bronze(
    definition: StrategyDefinition,
    *joker_names: str,
) -> StrategyDefinition:
    """Move weak standalone evidence to Bronze regardless of its previous tier."""

    tokens = _joker_tokens(*joker_names)
    return replace(
        definition,
        gold_jokers=frozenset(set(definition.gold_jokers) - set(tokens)),
        silver_jokers=frozenset(set(definition.silver_jokers) - set(tokens)),
        bronze_jokers=frozenset(set(definition.bronze_jokers) | set(tokens)),
    )


def _retire_standalone_strategy(definition: StrategyDefinition) -> StrategyDefinition:
    """Prevent active competition while preserving relationship metadata."""

    return replace(
        definition,
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
        "blackboard": ("Blackboard",),
        "flower_pot": ("Flower Pot",),
        "red_card": ("Red Card",),
        "no_discard_ramen": ("Ramen",),
        "last_hand_acrobat": ("Acrobat",),
        "no_discard_green": ("Green Joker",),
        "straight": ("Shortcut", "Four Fingers"),
        "sixes": ("Sixth Sense",),
        "aces": ("Scholar",),
        "queens_shoot_moon": ("Shoot the Moon",),
        "hiker_training": ("Hiker",),
        "loyalty_cycle": ("Loyalty Card",),
        "tarot_engine": ("Fortune Teller",),
        "tarot_cartomancer": ("Cartomancer",),
        "tarot_hallucination": ("Hallucination",),
        "tarot_eight_ball": ("8 Ball", "Eight Ball"),
        "joker_stencil": ("Joker Stencil",),
        "cash_growth": ("Rocket", "To the Moon"),
        "raised_fist": ("Raised Fist",),
    }
    for strategy_id, joker_names in weak_single_joker_cores.items():
        guarded[strategy_id] = _downgrade_gold_to_silver(
            guarded[strategy_id],
            *joker_names,
        )

    # Swashbuckler is the required scoring engine for this route. Egg and Gift
    # Card do not establish it by themselves, but once Swashbuckler is owned they
    # are Gold engine support because their sell-value growth directly increases
    # Swashbuckler's Mult.
    swashbuckler = guarded["swashbuckler"]
    guarded["swashbuckler"] = replace(
        swashbuckler,
        required_jokers=_joker_tokens("Swashbuckler"),
        gold_jokers=frozenset(
            set(swashbuckler.gold_jokers)
            | set(_joker_tokens("Egg", "Gift Card"))
        ),
    )

    # Sixth Sense alone is a utility generator rather than a sufficient scoring
    # engine. Tarot/consumable infrastructure may conditionally promote it back to
    # Silver, but its standalone Sixes evidence is only Bronze.
    guarded["sixes"] = _downgrade_to_bronze(
        guarded["sixes"],
        "Sixth Sense",
    )

    # Low-Rank Scoring is the Hack retrigger engine. Fibonacci, Even Steven and
    # low-rank deck shaping may strengthen it, but they cannot establish this route
    # without Hack. Raised Fist wants the same low cards retained in hand, so it is
    # an explicit conflict.
    low_rank = guarded["low_rank"]
    guarded["low_rank"] = replace(
        low_rank,
        required_jokers=_joker_tokens("Hack"),
        banned_jokers=frozenset(
            set(low_rank.banned_jokers) | set(_joker_tokens("Raised Fist"))
        ),
        entry_evidence_cap=0.0,
    )

    # Raised Fist remains a weak but real held-minimum route. Its defining Joker is
    # Silver rather than Gold, Mime is conditional Silver support, and Hack is banned.
    raised_fist = guarded["raised_fist"]
    guarded["raised_fist"] = replace(
        raised_fist,
        banned_jokers=frozenset(
            set(raised_fist.banned_jokers) | set(_joker_tokens("Hack"))
        ),
    )

    # Banner is weak reserve support while Delayed Gratification is the stronger
    # cash payoff. The package remains support-only but retains exact tier metadata.
    reserve = guarded["no_discard_reserve"]
    banner = _joker_tokens("Banner")
    delayed = _joker_tokens("Delayed Gratification")
    guarded["no_discard_reserve"] = replace(
        reserve,
        gold_jokers=frozenset(set(reserve.gold_jokers) - set(banner) - set(delayed)),
        silver_jokers=frozenset(set(reserve.silver_jokers) | set(delayed)),
        bronze_jokers=frozenset(set(reserve.bronze_jokers) | set(banner)),
    )

    # Support/economy mechanisms do not compete as standalone routes. Their tier
    # metadata remains available to relationship queries and support policies, but
    # the impossible defining requirement prevents positive standalone activation.
    non_standalone_strategy_ids = frozenset(
        {
            "abstract_joker",
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
