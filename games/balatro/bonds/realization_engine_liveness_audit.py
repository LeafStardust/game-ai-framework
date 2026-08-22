from __future__ import annotations

from dataclasses import replace
from typing import Any

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _jokers(state: Any) -> list[Any]:
    return list(getattr(state, "jokers", ()) or ())


def _has(values: list[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            return list(value or ())
    return []


def _debuffed(card: Any) -> bool:
    return bool(getattr(card, "debuffed", False) or getattr(card, "is_debuffed", False))


def _stone(card: Any) -> bool:
    return bool(getattr(card, "is_stone", False)) or str(getattr(card, "enhancement", "") or "").lower() == "stone"


def _finish(dev: BondDevelopment, active: bool, strong: bool = False) -> BondDevelopment:
    dev = enrich_development(dev)
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return replace(dev, realization=BondRealization.DORMANT)
    if not active:
        return replace(dev, realization=BondRealization.PARTIAL)
    if strong and dev.rank >= BondRank.R4:
        return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)


def _scoring_now(state: Any) -> bool:
    raw = getattr(state, "scoring_cards", None)
    if raw is not None:
        return bool(list(raw or ()))
    return bool(_cards(state, "cards_to_play", "played_cards", "current_played_cards"))


def _round_end(state: Any) -> bool:
    hands_left = getattr(state, "hands_left", None)
    return bool(
        getattr(state, "round_end_pending", False)
        or getattr(state, "last_hand_played", False)
        or (hands_left is not None and int(hands_left) == 0)
    )


def realize_cash_live(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    money = int(getattr(state, "money", 0) or 0)
    scoring = _scoring_now(state)
    round_end = _round_end(state)

    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    live_hand = [card for card in hand if not _debuffed(card)]
    pareidolia = _has(jokers, "pareidolia")
    face_held = bool(live_hand) if pareidolia else any(
        not _stone(card) and str(getattr(card, "rank", "") or "").upper() in {"J", "Q", "K"}
        for card in live_hand
    )

    deck = _cards(state, "owned_deck", "deck")
    nines = sum(1 for card in deck if not _stone(card) and str(getattr(card, "rank", "") or "").upper() == "9")
    planet_history = getattr(state, "unique_planets_used", getattr(state, "satellite_planets_used", None))
    satellite_planets = int(planet_history or 0) if planet_history is not None else 0

    scoring_sources = sum((
        _has(jokers, "bull") and scoring,
        _has(jokers, "bootstraps") and scoring and money >= 5,
        _has(jokers, "reservedparking") and scoring and face_held,
    ))
    end_sources = sum((
        _has(jokers, "goldenjoker") and round_end,
        _has(jokers, "rocket") and round_end,
        _has(jokers, "tothemoon") and round_end and money >= 5,
        _has(jokers, "cloud9") and round_end and nines > 0,
        _has(jokers, "satellite") and round_end and satellite_planets > 0,
    ))
    sources = scoring_sources + end_sources
    strong = sources >= 2 or (scoring and money >= 75 and (_has(jokers, "bull") or _has(jokers, "bootstraps")))
    return _finish(dev, sources > 0, strong)


def realize_no_discard_live(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state)
    scoring = _scoring_now(state)
    round_end = _round_end(state)
    blind_pending = bool(getattr(state, "blind_selection_pending", False))
    discards_used = int(getattr(state, "discards_used_this_round", 0) or 0)
    discards_left = int(getattr(state, "discards_left", getattr(state, "discards_remaining", 0)) or 0)

    # Green Joker gains Mult on every played hand, regardless of prior discards.
    # Ramen is also a scoring payoff regardless of whether a discard happened;
    # discarding only reduces its stored XMult. The other members have explicit
    # no-discard/remaining-discard trigger conditions.
    sources = sum((
        _has(jokers, "greenjoker") and scoring,
        _has(jokers, "burglar") and blind_pending,
        _has(jokers, "delayedgratification") and round_end and discards_used == 0,
        _has(jokers, "ramen") and scoring,
        _has(jokers, "banner") and scoring and discards_left > 0,
    ))
    return _finish(dev, sources > 0, sources >= 2)


ENGINE_LIVENESS_AUDIT_REALIZERS = {
    "cash": realize_cash_live,
    "no_discard": realize_no_discard_live,
}
