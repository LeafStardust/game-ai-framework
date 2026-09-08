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


def _is_stone(card: Any) -> bool:
    return bool(getattr(card, "is_stone", False)) or _enhancement(card) == "stone"


def _is_face(card: Any) -> bool:
    # Stone cards have no rank/suit identity for ordinary rank-sensitive effects.
    # Pareidolia is handled separately through ALL_CARDS_FACE and may restore face
    # identity for effects such as Midas Mask.
    if _is_stone(card):
        return False
    rank = str(getattr(card, "rank", "") or "").strip().upper()
    return rank in {"J", "Q", "K", "JACK", "QUEEN", "KING"}


def _live(card: Any) -> bool:
    return not bool(getattr(card, "debuffed", False))


def _mechanic_indices(jokers: list[Any], mechanic: str) -> tuple[int, ...]:
    return tuple(
        index
        for index, joker in enumerate(jokers)
        if components_have_mechanic((joker,), mechanic)
        and not bool(getattr(joker, "debuffed", False))
    )


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
    jokers = _jokers(state)
    vouchers = list(getattr(state, "vouchers", ()) or ())
    deck = _cards(state, "owned_deck", "deck")
    engine = components_have_mechanic(jokers, DISCARD_HAND_LEVELING) or components_have_mechanic(jokers, PROBABILISTIC_HAND_LEVELING)
    planet_access = components_have_mechanic(vouchers, PLANET_PACK_TARGETING)
    blue_seals = sum(1 for card in deck if str(getattr(card, "seal", "") or "").strip().lower() == "blue")
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
    jokers = _jokers(state)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    deck = _cards(state, "owned_deck", "deck")
    played = _cards(state, "scoring_cards", "played_cards", "current_played_cards")
    gold_owned = sum(1 for card in deck if _live(card) and _enhancement(card) == "gold")
    gold_held = sum(1 for card in hand if _live(card) and _enhancement(card) == "gold")
    gold_played = sum(1 for card in played if _live(card) and _enhancement(card) == "gold")
    generator = components_have_mechanic(jokers, GOLD_CARD_GENERATION)
    scoring_payoff = components_have_mechanic(jokers, GOLD_CARD_SCORING_ECONOMY)
    all_cards_face = components_have_mechanic(jokers, ALL_CARDS_FACE)
    scoring_face = any(_live(card) and (all_cards_face or _is_face(card)) for card in played)
    generator_live = generator and scoring_face
    active = gold_held > 0 or gold_owned >= 2 or generator_live or (scoring_payoff and gold_played > 0)
    strong = (gold_owned >= 5 and scoring_payoff) or (generator_live and scoring_payoff) or gold_held >= 3
    return _finish(dev, active=active, strong=strong)


def realize_enhancement_consumption(dev: BondDevelopment, state: Any) -> BondDevelopment:
    """Realize current triggerability plus persistent renewable feed structure."""
    jokers = _jokers(state)
    deck = _cards(state, "owned_deck", "deck")
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    played = _cards(state, "scoring_cards", "played_cards", "current_played_cards")
    consumer_indices = _mechanic_indices(jokers, ENHANCEMENT_CONSUMPTION)
    feed_indices = _mechanic_indices(jokers, ENHANCEMENT_FEED_ACCESS)
    consumer = bool(consumer_indices)
    all_cards_face = components_have_mechanic(jokers, ALL_CARDS_FACE)
    scoring_face = any(_live(card) and (all_cards_face or _is_face(card)) for card in played)
    ordered_same_hand_feed = scoring_face and any(
        feed_index < consumer_index
        for feed_index in feed_indices
        for consumer_index in consumer_indices
    )

    # Persistent enhanced cards remain structural feed even when temporarily
    # debuffed. Debuff only suppresses the immediate scoring trigger.
    persistent_feedstock = sum(1 for card in deck if bool(_enhancement(card)))
    hand_feedstock = sum(1 for card in hand if _live(card) and bool(_enhancement(card)))
    feedstock = persistent_feedstock if deck else hand_feedstock

    # Outside an active scoring window, Midas plus a face route is renewable future
    # feed even if Midas is to Vampire's right: generated Gold cards persist and can
    # be consumed on a later play. During the current scoring window, Joker order is
    # authoritative for same-hand feed.
    face_route = all_cards_face or any(_is_face(card) for card in (deck or hand))
    renewable_future_feed = bool(feed_indices) and face_route and not played
    consumed = int(getattr(state, "vampire_enhancements_consumed", 0) or 0)

    active = consumer and (feedstock > 0 or ordered_same_hand_feed or renewable_future_feed or consumed > 0)
    strong = consumer and ((ordered_same_hand_feed and feedstock > 0) or feedstock >= 6 or consumed >= 15)
    return _finish(dev, active=active, strong=strong)


CANONICAL_REALIZERS = {
    "hand_leveling": realize_hand_leveling,
    "gold_cards": realize_gold_cards,
    "enhancement_consumption": realize_enhancement_consumption,
}
