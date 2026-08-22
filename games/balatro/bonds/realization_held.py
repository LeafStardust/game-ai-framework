from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            return list(value or ())
    return []


def _jokers(state: Any) -> list[Any]:
    return list(getattr(state, "jokers", ()) or ())


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _rank(card: Any) -> str:
    return str(getattr(card, "rank", "") or "").upper()


def _suit(card: Any) -> str:
    return str(getattr(card, "suit", "") or "").lower()


def _enhancement(card: Any) -> str:
    return str(getattr(card, "enhancement", "") or "").lower()


def _seal(card: Any) -> str:
    return str(getattr(card, "seal", "") or "").lower()


def _development_floor(dev: BondDevelopment) -> BondRealization:
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return BondRealization.DORMANT
    return BondRealization.PARTIAL


def _mature_if_rank(dev: BondDevelopment, active: bool, strong: bool = False) -> BondRealization:
    if not active:
        return _development_floor(dev)
    if strong and dev.rank >= BondRank.R4:
        return BondRealization.MATURE
    return BondRealization.ACTIVE


def realize_held_cards(dev: BondDevelopment, state: Any) -> BondDevelopment:
    dev = enrich_development(dev)
    if _development_floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    jokers = _jokers(state)
    if not hand:
        return replace(dev, realization=BondRealization.PARTIAL)

    has_baron = _has(jokers, "baron")
    has_stm = _has(jokers, "shootthemoon")
    has_fist = _has(jokers, "raisedfist")
    has_blackboard = _has(jokers, "blackboard")

    king_hits = sum(1 for c in hand if _rank(c) == "K")
    queen_hits = sum(1 for c in hand if _rank(c) == "Q")
    steel_hits = sum(1 for c in hand if _enhancement(c) == "steel")
    blackboard_ok = bool(hand) and all(_suit(c) in {"spades", "clubs"} for c in hand if _enhancement(c) != "stone")

    active_sources = 0
    if has_baron and king_hits: active_sources += 1
    if has_stm and queen_hits: active_sources += 1
    if has_fist and hand: active_sources += 1
    if has_blackboard and blackboard_ok: active_sources += 1
    if steel_hits: active_sources += 1

    strong = active_sources >= 2 or king_hits + queen_hits + steel_hits >= 3
    return replace(dev, realization=_mature_if_rank(dev, active_sources > 0, strong))


def realize_held_retrigger(dev: BondDevelopment, state: Any) -> BondDevelopment:
    dev = enrich_development(dev)
    if _development_floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    jokers = _jokers(state)
    if not _has(jokers, "mime"):
        return replace(dev, realization=BondRealization.PARTIAL)
    if not hand:
        return replace(dev, realization=BondRealization.PARTIAL)

    retriggerable = 0
    for card in hand:
        if _enhancement(card) in {"steel", "gold"} or _seal(card) in {"blue", "red"}:
            retriggerable += 1
    if _has(jokers, "baron", "shootthemoon", "raisedfist"):
        retriggerable += 1

    return replace(dev, realization=_mature_if_rank(dev, retriggerable > 0, retriggerable >= 3))


def realize_steel(dev: BondDevelopment, state: Any) -> BondDevelopment:
    dev = enrich_development(dev)
    if _development_floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    if not hand:
        return replace(dev, realization=BondRealization.PARTIAL)
    held_steel = sum(1 for c in hand if _enhancement(c) == "steel")
    mime = _has(_jokers(state), "mime")
    strong = held_steel >= 3 or (held_steel >= 2 and mime)
    return replace(dev, realization=_mature_if_rank(dev, held_steel > 0, strong))


def realize_rank_held_payoff(dev: BondDevelopment, state: Any, rank: str, *joker_tokens: str) -> BondDevelopment:
    dev = enrich_development(dev)
    if _development_floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    if not hand:
        return replace(dev, realization=BondRealization.PARTIAL)
    count = sum(1 for c in hand if _rank(c) == rank)
    payoff_owned = _has(_jokers(state), *joker_tokens)
    active = count > 0 and payoff_owned
    strong = count >= 3 and payoff_owned
    return replace(dev, realization=_mature_if_rank(dev, active, strong))


def realize_kings(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_rank_held_payoff(dev, state, "K", "baron", "triboulet")


def realize_queens(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_rank_held_payoff(dev, state, "Q", "shootthemoon", "triboulet")


HELD_REALIZERS = {
    "held_cards": realize_held_cards,
    "held_retrigger": realize_held_retrigger,
    "steel": realize_steel,
    "kings": realize_kings,
    "queens": realize_queens,
}


def realize_held_family(dev: BondDevelopment, state: Any) -> BondDevelopment:
    fn = HELD_REALIZERS.get(dev.bond_id)
    if fn is None:
        return enrich_development(dev)
    return fn(dev, state)
