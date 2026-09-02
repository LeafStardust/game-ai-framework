from __future__ import annotations

from dataclasses import replace
from typing import Any

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.mechanics import (
    ALL_CARDS_FACE,
    DISCARD_HAND_LEVELING,
    ENHANCEMENT_CONSUMPTION,
    ENHANCEMENT_FEED_ACCESS,
    GOLD_CARD_GENERATION,
    GOLD_CARD_SCORING_ECONOMY,
    HELD_FACE_ECONOMY,
    PLANET_PACK_TARGETING,
    PROBABILISTIC_HAND_LEVELING,
    components_have_mechanic,
)


def _jokers(state: Any) -> list[Any]:
    return list(getattr(state, "jokers", ()) or ())


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        if hasattr(state, name):
            return list(getattr(state, name, None) or ())
    return []


def _enhancement(card: Any) -> str:
    return str(getattr(card, "enhancement", "") or "").strip().lower()


def _is_face(card: Any) -> bool:
    rank = str(getattr(card, "rank", "") or "").strip().upper()
    return rank in {"J", "Q", "K", "JACK", "QUEEN", "KING"}


def _finish(dev: BondDevelopment, *, active: bool, strong: bool = False) -> BondDevelopment:
    dev = enrich_development(dev)
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return replace(dev, realization=BondRealization.DORMANT)
    if not active:
        return replace(dev, realization=BondRealization.PARTIAL)
    if strong and dev.rank >= BondRank.R4:
        return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)


def realize_hand_leveling(dev: BondDevelopment, state: Any) -> BondDevelopment:
    """Realize persistent hand-level development from public mechanics."""
    jokers = _jokers(state)
    vouchers = list(getattr(state, "vouchers", ()) or ())
    deck = _cards(state, "owned_deck", "deck")

    engine = (
        components_have_mechanic(jokers, DISCARD_HAND_LEVELING)
        or components_have_mechanic(jokers, PROBABILISTIC_HAND_LEVELING)
    )
    planet_access = components_have_mechanic(vouchers, PLANET_PACK_TARGETING)
    blue_seals = sum(
        1 for card in deck
        if str(getattr(card, "seal", "") or "").strip().lower() == "blue"
    )

    target = dev.target or str(getattr(state, "target_hand", "") or "")
    levels = getattr(state, "hand_levels", {}) or {}
    target_level = 1
    if target:
        try:
            target_level = int(levels.get(target, 1) or 1)
        except (TypeError, ValueError):
            target_level = 1

    active = engine or planet_access or blue_seals > 0 or target_level > 1
    strong = sum((engine, planet_access, blue_seals >= 2, target_level >= 5)) >= 2
    return _finish(dev, active=active, strong=strong)


def realize_gold_cards(dev: BondDevelopment, state: Any) -> BondDevelopment:
    """Realize Gold-card infrastructure independently from generic cash value."""
    jokers = _jokers(state)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    deck = _cards(state, "owned_deck", "deck")
    played = _cards(state, "scoring_cards", "played_cards", "current_played_cards")

    gold_owned = sum(1 for card in deck if _enhancement(card) == "gold")
    gold_held = sum(1 for card in hand if _enhancement(card) == "gold")
    gold_played = sum(1 for card in played if _enhancement(card) == "gold")

    generator = components_have_mechanic(jokers, GOLD_CARD_GENERATION)
    payoff = (
        components_have_mechanic(jokers, GOLD_CARD_SCORING_ECONOMY)
        or components_have_mechanic(jokers, HELD_FACE_ECONOMY)
    )
    active = gold_held > 0 or gold_owned >= 2 or generator or (payoff and (gold_owned > 0 or gold_played > 0))
    strong = (gold_owned >= 5 and payoff) or (generator and payoff) or gold_held >= 3
    return _finish(dev, active=active, strong=strong)


def realize_enhancement_consumption(dev: BondDevelopment, state: Any) -> BondDevelopment:
    """Realize enhancement feed/consumption structure around an actual consumer."""
    jokers = _jokers(state)
    deck = _cards(state, "owned_deck", "deck")
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")

    consumer = components_have_mechanic(jokers, ENHANCEMENT_CONSUMPTION)
    has_feed_access = components_have_mechanic(jokers, ENHANCEMENT_FEED_ACCESS)
    all_cards_face = components_have_mechanic(jokers, ALL_CARDS_FACE)
    face_feed = all_cards_face or any(_is_face(card) for card in (deck or hand))
    renewable_feed = has_feed_access and face_feed
    feedstock = sum(1 for card in (deck or hand) if _enhancement(card))
    consumed = int(getattr(state, "vampire_enhancements_consumed", 0) or 0)

    # Feedstock before a consumer is useful acquisition evidence but only PARTIAL.
    # A face-dependent feed generator is renewable only when a face route exists.
    active = consumer and (feedstock > 0 or renewable_feed or consumed > 0)
    strong = consumer and ((renewable_feed and feedstock > 0) or feedstock >= 6 or consumed >= 15)
    return _finish(dev, active=active, strong=strong)


CANONICAL_REALIZERS = {
    "hand_leveling": realize_hand_leveling,
    "gold_cards": realize_gold_cards,
    "enhancement_consumption": realize_enhancement_consumption,
}
