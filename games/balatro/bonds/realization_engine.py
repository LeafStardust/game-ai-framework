from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            return list(value or ())
    return []


def _jokers(state: Any) -> list[Any]:
    return list(getattr(state, "jokers", ()) or ())


def _floor(dev: BondDevelopment) -> BondRealization:
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return BondRealization.DORMANT
    return BondRealization.PARTIAL


def _finish(dev: BondDevelopment, active: bool, strong: bool = False) -> BondDevelopment:
    dev = enrich_development(dev)
    if _floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)
    if not active:
        return replace(dev, realization=BondRealization.PARTIAL)
    if strong and dev.rank >= BondRank.R4:
        return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)


def realize_burnt(dev: BondDevelopment, state: Any) -> BondDevelopment:
    # Burnt functions when a first-discard opportunity remains and the run has a
    # target hand to level. Actual discard selection belongs to action search.
    discards_left = int(getattr(state, "discards_left", getattr(state, "discards_remaining", 0)) or 0)
    first_discard_available = bool(getattr(state, "first_discard_available", discards_left > 0))
    target = dev.target or str(getattr(state, "target_hand", "HIGH_CARD") or "HIGH_CARD")
    strong = first_discard_available and bool(target) and dev.rank >= BondRank.R4
    return _finish(dev, first_discard_available and bool(target), strong)


def realize_cash(dev: BondDevelopment, state: Any) -> BondDevelopment:
    money = int(getattr(state, "money", 0) or 0)
    jokers = _jokers(state)
    payoff = _has(jokers, "bull", "bootstraps")
    engine = _has(jokers, "rocket", "goldenjoker", "tothemoon", "satellite", "reservedparking", "cloud9")
    active = (payoff and money >= 25) or engine
    strong = (payoff and money >= 75) or (engine and money >= 50)
    return _finish(dev, active, strong)


def realize_no_discard(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    no_discard_payoff = _has(jokers, "greenjoker", "burglar", "delayedgratification", "ramen", "banner")
    discarded = int(getattr(state, "discards_used_this_round", 0) or 0)
    active = no_discard_payoff and discarded == 0
    return _finish(dev, active, active and len(jokers) >= 2)


def realize_tarot(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    consumables = _cards(state, "consumables", "consumable_cards")
    tarot_in_hand = any("tarot" in _name(c) or str(getattr(c, "set", "")).lower() == "tarot" for c in consumables)
    engine = _has(jokers, "cartomancer", "vagabond", "hallucination", "fortuneteller", "superposition", "8ball")
    active = tarot_in_hand or engine
    return _finish(dev, active, tarot_in_hand and engine)


def realize_planet(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    consumables = _cards(state, "consumables", "consumable_cards")
    planet_in_hand = any("planet" in _name(c) or str(getattr(c, "set", "")).lower() == "planet" for c in consumables)
    engine = _has(jokers, "constellation", "astronomer", "spacejoker")
    blue = any(str(getattr(c, "seal", "") or "").lower() == "blue" for c in _cards(state, "hand", "current_hand", "cards_in_hand"))
    active = planet_in_hand or engine or blue
    return _finish(dev, active, sum((planet_in_hand, engine, blue)) >= 2)


def realize_discard(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    discards_left = int(getattr(state, "discards_left", getattr(state, "discards_remaining", 0)) or 0)
    payoff = _has(jokers, "yorick", "castle", "mailinrebate", "facelessjoker", "hittheroad")
    active = payoff and discards_left > 0
    return _finish(dev, active, active and discards_left >= 2)


def realize_blind_skip(dev: BondDevelopment, state: Any) -> BondDevelopment:
    # Throwback itself is always live once owned; whether the current blind should
    # actually be skipped is a planner decision, not realization.
    active = _has(_jokers(state), "throwback")
    skipped = int(getattr(state, "blinds_skipped", 0) or 0)
    return _finish(dev, active, active and skipped >= 5)


def realize_sell_value(dev: BondDevelopment, state: Any) -> BondDevelopment:
    active = _has(_jokers(state), "swashbuckler") and int(getattr(state, "joker_sell_value_total", 0) or 0) > 0
    strong = active and int(getattr(state, "joker_sell_value_total", 0) or 0) >= 35
    return _finish(dev, active, strong)


def realize_joker_sacrifice(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    dagger = _has(jokers, "ceremonialdagger")
    madness = _has(jokers, "madness")
    fodder = bool(getattr(state, "sacrificable_joker_available", False)) or _has(jokers, "riffraff")
    blind_can_trigger = bool(getattr(state, "blind_selection_pending", True))
    active = (dagger and fodder) or (madness and blind_can_trigger)
    return _finish(dev, active, active and int(getattr(state, "jokers_destroyed", 0) or 0) >= 6)


def realize_card_destruction(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    trading = _has(jokers, "tradingcard") and bool(hand)
    sixth = _has(jokers, "sixthsense") and any(str(getattr(c, "rank", "")) == "6" for c in hand)
    glass = _has(jokers, "glassjoker") and any(str(getattr(c, "enhancement", "") or "").lower() == "glass" for c in hand)
    canio = _has(jokers, "canio") and int(getattr(state, "cards_destroyed", 0) or 0) > 0
    active = trading or sixth or glass or canio
    return _finish(dev, active, sum((trading, sixth, glass, canio)) >= 2)


def realize_hand_repetition(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    current = str(getattr(state, "current_hand_type", getattr(state, "last_hand_type", "")) or "").upper()
    previous = str(getattr(state, "previous_hand_type", "") or "").upper()
    cardsharp = _has(jokers, "cardsharp") and bool(current) and current == previous
    supernova = _has(jokers, "supernova") and bool(current)
    active = cardsharp or supernova
    repeated = max((int(v or 0) for v in (getattr(state, "hand_play_counts", {}) or {}).values()), default=0)
    return _finish(dev, active, active and repeated >= 18)


def realize_enhanced_cards(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if not _has(_jokers(state), "driverslicense"):
        return _finish(dev, False)
    deck = _cards(state, "owned_deck", "deck")
    enhanced = sum(1 for c in deck if str(getattr(c, "enhancement", "") or "").strip())
    # Driver's License turns on at 16 enhanced cards. Once that threshold is met,
    # the defining payoff is live; R4+ structural development is sufficient for
    # MATURE rather than inventing a second 24-card mechanical threshold.
    active = enhanced >= 16
    return _finish(dev, active, active)


def realize_vampire(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    if not _has(jokers, "vampire"):
        return _finish(dev, False)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    feed = sum(1 for c in hand if str(getattr(c, "enhancement", "") or "").strip())
    renewable = _has(jokers, "midasmask")
    active = feed > 0 or renewable
    return _finish(dev, active, feed >= 2 or (renewable and int(getattr(state, "vampire_enhancements_consumed", 0) or 0) >= 15))


ENGINE_REALIZERS = {
    "burnt": realize_burnt,
    "cash": realize_cash,
    "no_discard": realize_no_discard,
    "tarot": realize_tarot,
    "planet": realize_planet,
    "discard": realize_discard,
    "blind_skip": realize_blind_skip,
    "sell_value": realize_sell_value,
    "joker_sacrifice": realize_joker_sacrifice,
    "card_destruction": realize_card_destruction,
    "hand_repetition": realize_hand_repetition,
    "enhanced_cards": realize_enhanced_cards,
    "vampire": realize_vampire,
}


def realize_engine_family(dev: BondDevelopment, state: Any) -> BondDevelopment:
    fn = ENGINE_REALIZERS.get(dev.bond_id)
    return enrich_development(dev) if fn is None else fn(dev, state)
