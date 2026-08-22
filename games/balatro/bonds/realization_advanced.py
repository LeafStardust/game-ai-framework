from __future__ import annotations

from dataclasses import replace
from typing import Any

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


def _rank(card: Any) -> str:
    return str(getattr(card, "rank", "") or "").upper()


def _suit(card: Any) -> str:
    return str(getattr(card, "suit", "") or "").lower()


def _stone(card: Any) -> bool:
    return str(getattr(card, "enhancement", "") or "").lower() == "stone"


def _explicit_type(state: Any) -> str:
    return str(getattr(state, "current_hand_type", getattr(state, "best_hand_type", "")) or "").upper()


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
    suits: dict[str, set[int]] = {}
    rank_map = {"A":14,"K":13,"Q":12,"J":11,"10":10,"9":9,"8":8,"7":7,"6":6,"5":5,"4":4,"3":3,"2":2}
    for c in hand:
        s = _suit(c); r = rank_map.get(_rank(c))
        if s and r:
            suits.setdefault(s, set()).add(r)
    active = False
    for ranks in suits.values():
        seq = set(ranks)
        if 14 in seq: seq.add(1)
        vals = sorted(seq)
        for i in range(len(vals)-4):
            if vals[i+4]-vals[i] == 4 and len(set(vals[i:i+5])) == 5:
                active = True; break
        if active: break
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
    by_suit: dict[str, dict[str, int]] = {}
    for c in hand:
        s, r = _suit(c), _rank(c)
        if s and r:
            ranks = by_suit.setdefault(s, {})
            ranks[r] = ranks.get(r, 0) + 1
    active = False
    for ranks in by_suit.values():
        vals = sorted(ranks.values(), reverse=True)
        if len(vals) >= 2 and vals[0] >= 3 and vals[1] >= 2:
            active = True; break
    return _finish(dev, active, active)


def realize_flush_five(dev: BondDevelopment, state: Any) -> BondDevelopment:
    if _explicit_type(state) == "FLUSH_FIVE":
        return _finish(dev, True, True)
    groups: dict[tuple[str,str], int] = {}
    for c in _cards(state):
        if _stone(c): continue
        key = (_rank(c), _suit(c))
        if all(key): groups[key] = groups.get(key, 0) + 1
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
