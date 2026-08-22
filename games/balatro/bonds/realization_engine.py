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
    discards_left = int(getattr(state, "discards_left", getattr(state, "discards_remaining", 0)) or 0)
    discards_used = int(getattr(state, "discards_used_this_round", 0) or 0)
    first_discard_available = bool(getattr(state, "first_discard_available", discards_left > 0 and discards_used == 0))
    target = dev.target or str(getattr(state, "target_hand", "HIGH_CARD") or "HIGH_CARD")
    return _finish(dev, first_discard_available and bool(target), first_discard_available and bool(target) and dev.rank >= BondRank.R4)


def realize_cash(dev: BondDevelopment, state: Any) -> BondDevelopment:
    money = int(getattr(state, "money", 0) or 0); jokers = _jokers(state)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand"); deck = _cards(state, "owned_deck", "deck")
    pareidolia = _has(jokers, "pareidolia"); payoff = _has(jokers, "bull", "bootstraps")
    unconditional_engine = _has(jokers, "rocket", "goldenjoker"); interest_engine = _has(jokers, "tothemoon") and money >= 5
    held_faces = bool(hand) if pareidolia else any(str(getattr(c, "rank", "") or "").upper() in {"J", "Q", "K"} for c in hand)
    parking_engine = _has(jokers, "reservedparking") and held_faces
    cloud9_engine = _has(jokers, "cloud9") and any(str(getattr(c, "rank", "") or "") == "9" for c in deck)
    satellite = _has(jokers, "satellite"); planet_history = getattr(state, "unique_planets_used", getattr(state, "satellite_planets_used", None))
    satellite_engine = satellite and (planet_history is None or int(planet_history or 0) > 0)
    engine_sources = sum((unconditional_engine, interest_engine, parking_engine, cloud9_engine, satellite_engine))
    return _finish(dev, (payoff and money >= 25) or engine_sources > 0, (payoff and money >= 75) or engine_sources >= 2 or (engine_sources > 0 and money >= 50))


def realize_no_discard(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); source_tokens = ("greenjoker", "burglar", "delayedgratification", "ramen", "banner")
    source_count = sum(1 for token in source_tokens if _has(jokers, token)); discarded = int(getattr(state, "discards_used_this_round", 0) or 0)
    active = source_count > 0 and discarded == 0; return _finish(dev, active, active and source_count >= 2)


def realize_tarot(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); vouchers = list(getattr(state, "vouchers", ()) or ()); consumables = _cards(state, "consumables", "consumable_cards")
    tarot_in_hand = any("tarot" in _name(c) or str(getattr(c, "set", "")).lower() == "tarot" for c in consumables)
    engine = _has(jokers, "cartomancer", "vagabond", "hallucination", "fortuneteller", "superposition", "8ball", "eightball")
    shop = _has(vouchers, "tarotmerchant", "tarottycoon"); return _finish(dev, tarot_in_hand or engine or shop, sum((tarot_in_hand, engine, shop)) >= 2)


def realize_planet(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); vouchers = list(getattr(state, "vouchers", ()) or ()); consumables = _cards(state, "consumables", "consumable_cards")
    planet = any("planet" in _name(c) or str(getattr(c, "set", "")).lower() == "planet" for c in consumables); engine = _has(jokers, "constellation", "astronomer", "spacejoker")
    blue = any(str(getattr(c, "seal", "") or "").lower() == "blue" for c in _cards(state, "hand", "current_hand", "cards_in_hand")); shop = _has(vouchers, "planetmerchant", "planettycoon", "telescope")
    return _finish(dev, planet or engine or blue or shop, sum((planet, engine, blue, shop)) >= 2)


def realize_discard(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); left = int(getattr(state, "discards_left", getattr(state, "discards_remaining", 0)) or 0); payoff = _has(jokers, "yorick", "castle", "mailinrebate", "facelessjoker", "hittheroad")
    active = payoff and left > 0; return _finish(dev, active, active and left >= 2)


def realize_blind_skip(dev: BondDevelopment, state: Any) -> BondDevelopment:
    active = _has(_jokers(state), "throwback"); skipped = int(getattr(state, "blinds_skipped", 0) or 0); return _finish(dev, active, active and skipped >= 5)


def realize_sell_value(dev: BondDevelopment, state: Any) -> BondDevelopment:
    total = int(getattr(state, "joker_sell_value_total", 0) or 0); active = _has(_jokers(state), "swashbuckler") and total > 0; return _finish(dev, active, active and total >= 35)


def realize_joker_sacrifice(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); dagger_index = next((i for i, j in enumerate(jokers) if "ceremonialdagger" in _name(j)), None)
    dagger_has_target = dagger_index is not None and dagger_index + 1 < len(jokers)
    ordered_fodder = dagger_has_target and (bool(getattr(state, "sacrificable_joker_available", False)) or "riffraff" in _name(jokers[dagger_index + 1]))
    madness = _has(jokers, "madness"); pending = bool(getattr(state, "blind_selection_pending", True)); active = ordered_fodder or (madness and pending)
    return _finish(dev, active, active and int(getattr(state, "jokers_destroyed", 0) or 0) >= 6)


def realize_card_destruction(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    first_discard = bool(getattr(state, "first_discard_available", int(getattr(state, "discards_used_this_round", 0) or 0) == 0)); first_hand = bool(getattr(state, "first_hand_available", int(getattr(state, "hands_played_this_round", 0) or 0) == 0))
    selected_discard = _cards(state, "selected_cards", "cards_to_discard")
    selected_play = _cards(state, "cards_to_play", "selected_cards")
    trading = _has(jokers, "tradingcard") and first_discard and len(selected_discard) == 1
    sixth = _has(jokers, "sixthsense") and first_hand and len(selected_play) == 1 and str(getattr(selected_play[0], "rank", "")) == "6"
    glass = _has(jokers, "glassjoker") and any(str(getattr(c, "enhancement", "") or "").lower() == "glass" for c in hand); canio = _has(jokers, "canio") and int(getattr(state, "cards_destroyed", 0) or 0) > 0
    active = trading or sixth or glass or canio; return _finish(dev, active, sum((trading, sixth, glass, canio)) >= 2)


def realize_hand_repetition(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state); current = str(getattr(state, "current_hand_type", getattr(state, "last_hand_type", "")) or "").upper().replace(" ", "_")
    counts = getattr(state, "hand_play_counts", {}) or {}; normalized = {str(k).upper().replace(" ", "_"): int(v or 0) for k, v in counts.items()}; prior = normalized.get(current, 0) if current else 0
    previous = str(getattr(state, "previous_hand_type", "") or "").upper().replace(" ", "_"); history = prior > 0 if normalized else bool(current) and current == previous
    cardsharp = _has(jokers, "cardsharp") and bool(current) and history; supernova = _has(jokers, "supernova") and bool(current); active = cardsharp or supernova
    return _finish(dev, active, active and max(normalized.values(), default=0) >= 18)


def realize_enhanced_cards(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if not _has(_jokers(state), "driverslicense"): return _finish(dev, False)
    enhanced = sum(1 for c in _cards(state, "owned_deck", "deck") if str(getattr(c, "enhancement", "") or "").strip()); active = enhanced >= 16; return _finish(dev, active, active)


def realize_vampire(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    if not _has(jokers, "vampire"): return _finish(dev, False)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand"); deck = _cards(state, "owned_deck", "deck")
    scoring_raw = getattr(state, "scoring_cards", None)
    if scoring_raw is not None:
        scoring = list(scoring_raw or ()); feed_cards = scoring
    else:
        scoring = _cards(state, "played_cards", "current_played_cards"); feed_cards = scoring or hand
    feed = sum(1 for c in feed_cards if str(getattr(c, "enhancement", "") or "").strip())
    has_midas = _has(jokers, "midasmask"); pareidolia = _has(jokers, "pareidolia")
    face_pool = scoring if scoring_raw is not None else (scoring or hand or deck)
    face_available = bool(face_pool) if pareidolia else any(str(getattr(c, "rank", "") or "").upper() in {"J", "Q", "K"} for c in face_pool)
    renewable = has_midas and face_available; active = feed > 0 or renewable
    return _finish(dev, active, feed >= 2 or (renewable and int(getattr(state, "vampire_enhancements_consumed", 0) or 0) >= 15))


ENGINE_REALIZERS = {"burnt": realize_burnt, "cash": realize_cash, "no_discard": realize_no_discard, "tarot": realize_tarot, "planet": realize_planet, "discard": realize_discard, "blind_skip": realize_blind_skip, "sell_value": realize_sell_value, "joker_sacrifice": realize_joker_sacrifice, "card_destruction": realize_card_destruction, "hand_repetition": realize_hand_repetition, "enhanced_cards": realize_enhanced_cards, "vampire": realize_vampire}


def realize_engine_family(dev: BondDevelopment, state: Any) -> BondDevelopment:
    fn = ENGINE_REALIZERS.get(dev.bond_id); return enrich_development(dev) if fn is None else fn(dev, state)
