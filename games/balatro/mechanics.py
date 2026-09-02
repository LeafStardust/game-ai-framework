from __future__ import annotations

"""Canonical public mechanical descriptors for persistent Balatro components.

Strategic systems should query these mechanics instead of branching on Joker or
component display names. Mechanically modeled classes expose ``mechanics``
directly. The name fallback exists only for public snapshot/test objects that do
not carry the concrete runtime class yet and should shrink as those objects gain
native descriptors.
"""

from typing import Any, Iterable


DISCARD_HAND_LEVELING = "discard_hand_leveling"
PROBABILISTIC_HAND_LEVELING = "probabilistic_hand_leveling"
HAND_LEVEL_COPY = "hand_level_copy"
PLANET_PACK_TARGETING = "planet_pack_targeting"
PLANET_GENERATION = "planet_generation"
PLANET_SCALING = "planet_scaling"
PLANET_SHOP_ACCESS = "planet_shop_access"
PLANET_SHOP_ACCESS_MAJOR = "planet_shop_access_major"
GOLD_CARD_GENERATION = "gold_card_generation"
GOLD_CARD_SCORING_ECONOMY = "gold_card_scoring_economy"
HELD_FACE_ECONOMY = "held_face_economy"
ENHANCEMENT_CONSUMPTION = "enhancement_consumption"
ENHANCEMENT_FEED_ACCESS = "enhancement_feed_access"
ENHANCEMENT_DENSITY_PAYOFF = "enhancement_density_payoff"
ENHANCEMENT_GENERATION = "enhancement_generation"
TAROT_GENERATION = "tarot_generation"
TAROT_LOW_MONEY_GENERATION = "tarot_low_money_generation"
TAROT_PACK_GENERATION = "tarot_pack_generation"
TAROT_SCORING_EIGHT_GENERATION = "tarot_scoring_eight_generation"
TAROT_STRAIGHT_ACE_GENERATION = "tarot_straight_ace_generation"
TAROT_SCALING = "tarot_scaling"
TAROT_SHOP_ACCESS = "tarot_shop_access"
TAROT_SHOP_ACCESS_MAJOR = "tarot_shop_access_major"
ALL_CARDS_FACE = "all_cards_face"
RETRIGGER_HELD_CARDS = "retrigger_held_cards"
STEEL_CARD_PAYOFF = "steel_card_payoff"
CARD_DESTRUCTION = "card_destruction"
FACE_DESTRUCTION_SCALING = "face_destruction_scaling"
GLASS_DESTRUCTION_SCALING = "glass_destruction_scaling"
DECK_THIN_PAYOFF = "deck_thin_payoff"
SPECTRAL_GENERATION = "spectral_generation"

HELD_KING_XMULT = "held_king_xmult"
PLAYED_KING_QUEEN_XMULT = "played_king_queen_xmult"
HELD_QUEEN_MULT = "held_queen_mult"
DISCARD_JACK_XMULT = "discard_jack_xmult"

RANK_PAYOFF_KINGS = "rank_payoff:kings"
RANK_PAYOFF_QUEENS = "rank_payoff:queens"
RANK_PAYOFF_JACKS = "rank_payoff:jacks"

DISCARD_SCALING = "discard_scaling"
DISCARD_SUIT_SCALING = "discard_suit_scaling"
DISCARD_RANK_ECONOMY = "discard_rank_economy"
DISCARD_FACE_ECONOMY = "discard_face_economy"
DISCARD_JACK_SCALING = "discard_jack_scaling"

BLIND_SKIP_SCALING = "blind_skip_scaling"
BLIND_SKIP_TAG_GENERATION = "blind_skip_tag_generation"
SELL_VALUE_SCORING = "sell_value_scoring"
GLOBAL_SELL_VALUE_GROWTH = "global_sell_value_growth"
SELF_SELL_VALUE_GROWTH = "self_sell_value_growth"
LEFT_JOKER_SACRIFICE = "left_joker_sacrifice"
RANDOM_JOKER_SACRIFICE = "random_joker_sacrifice"
JOKER_FODDER_GENERATION = "joker_fodder_generation"
HAND_REPETITION_XMULT = "hand_repetition_xmult"
HAND_REPETITION_SCALING = "hand_repetition_scaling"


def _normalize_name(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = getattr(value, "name", None)
        if raw is None:
            raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


# Compatibility-only semantics for state snapshots and lightweight test objects.
# Runtime Joker classes should expose their mechanics directly.
_LEGACY_NAME_MECHANICS: dict[str, frozenset[str]] = {
    "burntjoker": frozenset({DISCARD_HAND_LEVELING}),
    "spacejoker": frozenset({PROBABILISTIC_HAND_LEVELING, PLANET_GENERATION}),
    "blueprint": frozenset({HAND_LEVEL_COPY}),
    "blueprintjoker": frozenset({HAND_LEVEL_COPY}),
    "brainstorm": frozenset({HAND_LEVEL_COPY}),
    "brainstormjoker": frozenset({HAND_LEVEL_COPY}),
    "telescope": frozenset({PLANET_PACK_TARGETING}),
    "planetmerchant": frozenset({PLANET_SHOP_ACCESS}),
    "planettycoon": frozenset({PLANET_SHOP_ACCESS_MAJOR}),
    "constellation": frozenset({PLANET_SCALING}),
    "astronomer": frozenset({PLANET_GENERATION}),
    "midasmask": frozenset({GOLD_CARD_GENERATION, ENHANCEMENT_FEED_ACCESS, ENHANCEMENT_GENERATION}),
    "midasmaskjoker": frozenset({GOLD_CARD_GENERATION, ENHANCEMENT_FEED_ACCESS, ENHANCEMENT_GENERATION}),
    "goldenticket": frozenset({GOLD_CARD_SCORING_ECONOMY}),
    "goldenticketjoker": frozenset({GOLD_CARD_SCORING_ECONOMY}),
    "reservedparking": frozenset({HELD_FACE_ECONOMY}),
    "reservedparkingjoker": frozenset({HELD_FACE_ECONOMY}),
    "vampire": frozenset({ENHANCEMENT_CONSUMPTION}),
    "vampirejoker": frozenset({ENHANCEMENT_CONSUMPTION}),
    "cartomancer": frozenset({TAROT_GENERATION}),
    "cartomancerjoker": frozenset({TAROT_GENERATION}),
    "vagabond": frozenset({TAROT_LOW_MONEY_GENERATION}),
    "hallucination": frozenset({TAROT_PACK_GENERATION}),
    "fortuneteller": frozenset({TAROT_SCALING}),
    "8ball": frozenset({TAROT_SCORING_EIGHT_GENERATION}),
    "eightball": frozenset({TAROT_SCORING_EIGHT_GENERATION}),
    "superposition": frozenset({TAROT_STRAIGHT_ACE_GENERATION}),
    "tarotmerchant": frozenset({TAROT_SHOP_ACCESS}),
    "tarottycoon": frozenset({TAROT_SHOP_ACCESS_MAJOR}),
    "pareidolia": frozenset({ALL_CARDS_FACE}),
    "pareidoliajoker": frozenset({ALL_CARDS_FACE}),
    "mime": frozenset({RETRIGGER_HELD_CARDS}),
    "mimejoker": frozenset({RETRIGGER_HELD_CARDS}),
    "steeljoker": frozenset({STEEL_CARD_PAYOFF}),
    "tradingcard": frozenset({CARD_DESTRUCTION}),
    "tradingcardjoker": frozenset({CARD_DESTRUCTION}),
    "erosion": frozenset({DECK_THIN_PAYOFF}),
    "erosionjoker": frozenset({DECK_THIN_PAYOFF}),
    "sixthsense": frozenset({CARD_DESTRUCTION, SPECTRAL_GENERATION}),
    "sixthsensejoker": frozenset({CARD_DESTRUCTION, SPECTRAL_GENERATION}),
    "canio": frozenset({FACE_DESTRUCTION_SCALING}),
    "glassjoker": frozenset({GLASS_DESTRUCTION_SCALING}),
    "baron": frozenset({HELD_KING_XMULT, RANK_PAYOFF_KINGS}),
    "baronjoker": frozenset({HELD_KING_XMULT, RANK_PAYOFF_KINGS}),
    "triboulet": frozenset({PLAYED_KING_QUEEN_XMULT, RANK_PAYOFF_KINGS, RANK_PAYOFF_QUEENS}),
    "shootthemoon": frozenset({HELD_QUEEN_MULT, RANK_PAYOFF_QUEENS}),
    "shootthemoonjoker": frozenset({HELD_QUEEN_MULT, RANK_PAYOFF_QUEENS}),
    "hittheroad": frozenset({DISCARD_JACK_XMULT, RANK_PAYOFF_JACKS, DISCARD_JACK_SCALING}),
    "yorick": frozenset({DISCARD_SCALING}),
    "castle": frozenset({DISCARD_SUIT_SCALING}),
    "mailinrebate": frozenset({DISCARD_RANK_ECONOMY}),
    "facelessjoker": frozenset({DISCARD_FACE_ECONOMY}),
    "throwback": frozenset({BLIND_SKIP_SCALING}),
    "dietcola": frozenset({BLIND_SKIP_TAG_GENERATION}),
    "swashbuckler": frozenset({SELL_VALUE_SCORING}),
    "giftcard": frozenset({GLOBAL_SELL_VALUE_GROWTH}),
    "egg": frozenset({SELF_SELL_VALUE_GROWTH}),
    "eggjoker": frozenset({SELF_SELL_VALUE_GROWTH}),
    "ceremonialdagger": frozenset({LEFT_JOKER_SACRIFICE}),
    "madness": frozenset({RANDOM_JOKER_SACRIFICE}),
    "riffraff": frozenset({JOKER_FODDER_GENERATION}),
    "cardsharp": frozenset({HAND_REPETITION_XMULT}),
    "supernova": frozenset({HAND_REPETITION_SCALING}),
    "driverslicense": frozenset({ENHANCEMENT_DENSITY_PAYOFF}),
    "marblejoker": frozenset({ENHANCEMENT_GENERATION}),
}


def component_mechanics(component: Any) -> frozenset[str]:
    """Return public persistent mechanics exposed by one component."""
    declared = getattr(component, "mechanics", None)
    if declared is not None:
        if callable(declared):
            declared = declared()
        return frozenset(str(item) for item in (declared or ()))
    return _LEGACY_NAME_MECHANICS.get(_normalize_name(component), frozenset())


def component_has_mechanic(component: Any, mechanic: str) -> bool:
    return mechanic in component_mechanics(component)


def components_have_mechanic(values: Iterable[Any], mechanic: str) -> bool:
    return any(component_has_mechanic(value, mechanic) for value in values)


def components_with_mechanic(values: Iterable[Any], mechanic: str) -> tuple[Any, ...]:
    return tuple(value for value in values if component_has_mechanic(value, mechanic))
