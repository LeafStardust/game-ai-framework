from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _floor(dev: BondDevelopment) -> BondRealization:
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return BondRealization.DORMANT
    return BondRealization.PARTIAL


def _cards(state: Any) -> list[Any]:
    for name in ("hand", "current_hand", "cards_in_hand"):
        value = getattr(state, name, None)
        if value is not None:
            return list(value or ())
    return []


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(value) for value in values}
    return any(any(token in name for name in names) for token in tokens)


def _rank(card: Any) -> str:
    return str(getattr(card, "rank", "") or "").upper()


def _suit(card: Any) -> str:
    return str(getattr(card, "suit", "") or "").lower()


def _enh(card: Any) -> str:
    return str(getattr(card, "enhancement", "") or "").lower()


def _stone(card: Any) -> bool:
    return _enh(card) == "stone"


def _explicit_type(state: Any) -> str:
    raw = getattr(state, "current_hand_type", None) or getattr(state, "best_hand_type", "")
    return str(raw or "").upper().replace(" ", "_")


def _finish(dev: BondDevelopment, active: bool, strong: bool = False) -> BondDevelopment:
    dev = enrich_development(dev)
    if _floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)
    if not active:
        return replace(dev, realization=BondRealization.PARTIAL)
    if strong and dev.rank >= BondRank.R4:
        return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)


def _counts(hand: list[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in hand:
        if _stone(c):
            continue
        r = _rank(c)
        if r:
            out[r] = out.get(r, 0) + 1
    return out


def _effective_suits(card: Any, smeared: bool) -> tuple[str, ...]:
    # Wild cards count as every suit. Under Smeared Joker, those four suits
    # collapse into the two color-equivalence classes used by flush logic.
    if _enh(card) == "wild":
        return ("red", "black") if smeared else ("hearts", "diamonds", "spades", "clubs")
    suit = _suit(card)
    if not smeared:
        return (suit,) if suit else ()
    if suit in {"hearts", "diamonds"}:
        return ("red",)
    if suit in {"spades", "clubs"}:
        return ("black",)
    return (suit,) if suit else ()


def _straight_available(ranks: set[int], *, needed: int, shortcut: bool) -> bool:
    if 14 in ranks:
        ranks = set(ranks)
        ranks.add(1)
    vals = sorted(ranks)
    if len(vals) < needed:
        return False
    max_gap = 2 if shortcut else 1
    for start in range(len(vals)):
        length = 1
        prev = vals[start]
        for value in vals[start + 1:]:
            gap = value - prev
            if gap <= 0:
                continue
            if gap > max_gap:
                break
            length += 1
            prev = value
            if length >= needed:
                return True
    return needed <= 1


def realize_full_house(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if _explicit_type(state) == "FULL_HOUSE":
        return _finish(dev, True, True)
    vals = sorted(_counts(_cards(state)).values(), reverse=True)
    active = len(vals) >= 2 and vals[0] >= 3 and vals[1] >= 2
    return _finish(dev, active, active)


def realize_straight_flush(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if _explicit_type(state) == "STRAIGHT_FLUSH":
        return _finish(dev, True, True)
    hand = [c for c in _cards(state) if not _stone(c)]
    jokers = list(getattr(state, "jokers", ()) or ())
    four_fingers = _has(jokers, "fourfingers")
    shortcut = _has(jokers, "shortcut")
    smeared = _has(jokers, "smearedjoker", "smeared")
    needed = 4 if four_fingers else 5
    rank_map = {"A":14,"K":13,"Q":12,"J":11,"10":10,"T":10,"9":9,"8":8,"7":7,"6":6,"5":5,"4":4,"3":3,"2":2}
    suits: dict[str, set[int]] = {}
    for c in hand:
        rank = rank_map.get(_rank(c))
        if not rank:
            continue
        for suit in _effective_suits(c, smeared):
            suits.setdefault(suit, set()).add(rank)
    active = any(_straight_available(ranks, needed=needed, shortcut=shortcut) for ranks in suits.values())
    return _finish(dev, active, active)


def realize_five_kind(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if _explicit_type(state) == "FIVE_OF_A_KIND":
        return _finish(dev, True, True)
    active = max(_counts(_cards(state)).values(), default=0) >= 5
    return _finish(dev, active, active)


def realize_flush_house(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if _explicit_type(state) == "FLUSH_HOUSE":
        return _finish(dev, True, True)
    hand = [c for c in _cards(state) if not _stone(c)]
    smeared = _has(list(getattr(state, "jokers", ()) or ()), "smearedjoker", "smeared")
    by_suit: dict[str, dict[str, int]] = {}
    for c in hand:
        rank = _rank(c)
        if not rank:
            continue
        for suit in _effective_suits(c, smeared):
            ranks = by_suit.setdefault(suit, {})
            ranks[rank] = ranks.get(rank, 0) + 1
    active = False
    for ranks in by_suit.values():
        vals = sorted(ranks.values(), reverse=True)
        if len(vals) >= 2 and vals[0] >= 3 and vals[1] >= 2:
            active = True
            break
    return _finish(dev, active, active)


def realize_flush_five(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if _explicit_type(state) == "FLUSH_FIVE":
        return _finish(dev, True, True)
    smeared = _has(list(getattr(state, "jokers", ()) or ()), "smearedjoker", "smeared")
    groups: dict[tuple[str, str], int] = {}
    for c in _cards(state):
        if _stone(c):
            continue
        rank = _rank(c)
        if not rank:
            continue
        for suit in _effective_suits(c, smeared):
            key = (rank, suit)
            groups[key] = groups.get(key, 0) + 1
    active = max(groups.values(), default=0) >= 5
    return _finish(dev, active, active)


ADVANCED_REALIZERS = {
    "full_house": realize_full_house,
    "straight_flush": realize_straight_flush,
    "five_kind": realize_five_kind,
    "flush_house": realize_flush_house,
    "flush_five": realize_flush_five,
}


def realize_advanced_family(dev: BondDevelopment, state: Any) -> BondDevelopment:
    fn = ADVANCED_REALIZERS.get(dev.bond_id)
    return enrich_development(dev) if fn is None else fn(dev, state)
