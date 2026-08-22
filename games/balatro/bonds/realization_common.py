from __future__ import annotations

from collections import Counter
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


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned or ())
    return list(getattr(state, "deck", ()) or ())


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


def _seal(card: Any) -> str:
    return str(getattr(card, "seal", "") or "").lower()


def _stone(card: Any) -> bool:
    return bool(getattr(card, "is_stone", False)) or str(getattr(card, "enhancement", "") or "").lower() == "stone"


def _floor(dev: BondDevelopment) -> BondRealization:
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return BondRealization.DORMANT
    return BondRealization.PARTIAL


def _finish(dev: BondDevelopment, *, active: bool, strong: bool = False) -> BondDevelopment:
    if not active:
        return replace(dev, realization=_floor(dev))
    if strong and dev.rank >= BondRank.R4:
        return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)


def _known_hand_type(state: Any) -> str:
    for name in ("current_hand_type", "best_hand_type", "selected_hand_type", "hand_type"):
        value = getattr(state, name, None)
        if value:
            return str(value).upper().replace(" ", "_")
    return ""


def _hand_shape(cards: list[Any]) -> set[str]:
    natural = [c for c in cards if not _stone(c)]
    ranks = Counter(_rank(c) for c in natural if _rank(c))
    counts = sorted(ranks.values(), reverse=True)
    shapes: set[str] = set()
    if natural:
        shapes.add("HIGH_CARD")
    if counts and counts[0] >= 2:
        shapes.add("PAIR")
    if len([n for n in counts if n >= 2]) >= 2:
        shapes.add("TWO_PAIR")
    if counts and counts[0] >= 3:
        shapes.add("THREE_OF_A_KIND")
    if counts and counts[0] >= 4:
        shapes.add("FOUR_OF_A_KIND")

    values = {"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"T":10,"J":11,"Q":12,"K":13,"A":14}
    nums = sorted({values[r] for r in ranks if r in values})
    ace_low = 14 in nums and {2,3,4,5}.issubset(nums)
    straight = ace_low or any(all(v in nums for v in range(start, start + 5)) for start in range(2, 11))
    if straight:
        shapes.add("STRAIGHT")

    suit_counts = Counter(_suit(c) for c in natural if _suit(c))
    if any(v >= 5 for v in suit_counts.values()):
        shapes.add("FLUSH")
    return shapes


def realize_hand_bond(dev: BondDevelopment, state: Any, hand_type: str) -> BondDevelopment:
    dev = enrich_development(dev)
    if _floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    known = _known_hand_type(state)
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    active = known == hand_type or hand_type in _hand_shape(hand)
    # A mature hand Bond needs both high structural authority and evidence the
    # hand is currently available, plus repeatability evidence when exposed.
    repeatable = bool(getattr(state, "target_hand_repeatable", False) or getattr(state, "hand_consistency_high", False))
    return _finish(dev, active=active, strong=active and repeatable)


def realize_pair(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "PAIR")


def realize_high_card(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "HIGH_CARD")


def realize_two_pair(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "TWO_PAIR")


def realize_three_kind(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "THREE_OF_A_KIND")


def realize_four_kind(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "FOUR_OF_A_KIND")


def realize_straight(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "STRAIGHT")


def realize_flush(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return realize_hand_bond(dev, state, "FLUSH")


def realize_played_retrigger(dev: BondDevelopment, state: Any) -> BondDevelopment:
    dev = enrich_development(dev)
    if _floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    jokers = list(getattr(state, "jokers", ()) or ())
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    played = _cards(state, "selected_cards", "cards_to_play", "scoring_cards") or hand
    red_seal = sum(1 for c in played if _seal(c) == "red")
    face = sum(1 for c in played if _rank(c) in {"J", "Q", "K"})
    low = sum(1 for c in played if _rank(c) in {"2", "3", "4", "5"})

    sources = 0
    if _has(jokers, "sockandbuskin") and face:
        sources += 1
    if _has(jokers, "hack") and low:
        sources += 1
    if _has(jokers, "hangingchad") and played:
        sources += 1
    if _has(jokers, "dusk") and played and int(getattr(state, "hands_left", 2) or 2) == 1:
        sources += 1
    if red_seal:
        sources += 1

    strong = sources >= 2 or red_seal >= 2
    return _finish(dev, active=sources > 0, strong=strong)


def realize_deck_thinning(dev: BondDevelopment, state: Any) -> BondDevelopment:
    dev = enrich_development(dev)
    if _floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    deck = _deck(state)
    reduction = max(0, 52 - len(deck)) if deck else int(getattr(state, "permanent_cards_removed", 0) or 0)
    jokers = list(getattr(state, "jokers", ()) or ())
    payoff = _has(jokers, "erosion") and reduction > 0
    engine = _has(jokers, "tradingcard", "sixthsense")
    active = reduction > 0 and (payoff or engine or dev.rank >= BondRank.R2)
    strong = reduction >= 12 and (payoff or engine)
    return _finish(dev, active=active, strong=strong)


def realize_deck_growth(dev: BondDevelopment, state: Any) -> BondDevelopment:
    dev = enrich_development(dev)
    if _floor(dev) == BondRealization.DORMANT:
        return replace(dev, realization=BondRealization.DORMANT)

    deck = _deck(state)
    growth = max(0, len(deck) - 52) if deck else int(getattr(state, "permanent_cards_added", 0) or 0)
    jokers = list(getattr(state, "jokers", ()) or ())
    engine = _has(jokers, "certificate", "dna", "marblejoker", "hologram")
    payoff = _has(jokers, "hologram") and growth > 0
    active = growth > 0 and (engine or dev.rank >= BondRank.R2)
    strong = growth >= 12 and (payoff or engine)
    return _finish(dev, active=active, strong=strong)


COMMON_REALIZERS = {
    "pair": realize_pair,
    "high_card": realize_high_card,
    "two_pair": realize_two_pair,
    "three_kind": realize_three_kind,
    "four_kind": realize_four_kind,
    "straight": realize_straight,
    "flush": realize_flush,
    "played_retrigger": realize_played_retrigger,
    "deck_thinning": realize_deck_thinning,
    "deck_growth": realize_deck_growth,
}


def realize_common_family(dev: BondDevelopment, state: Any) -> BondDevelopment:
    fn = COMMON_REALIZERS.get(dev.bond_id)
    if fn is None:
        return enrich_development(dev)
    return fn(dev, state)
