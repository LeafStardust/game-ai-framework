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


def _enh(card: Any) -> str:
    return str(getattr(card, "enhancement", "") or "").lower()


def _floor(dev: BondDevelopment) -> BondRealization:
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return BondRealization.DORMANT
    return BondRealization.PARTIAL


def _finish(dev: BondDevelopment, active: bool, strong: bool = False) -> BondDevelopment:
    if _floor(dev) == BondRealization.DORMANT:
        return replace(enrich_development(dev), realization=BondRealization.DORMANT)
    realization = BondRealization.MATURE if active and strong and dev.rank >= BondRank.R4 else BondRealization.ACTIVE if active else BondRealization.PARTIAL
    return replace(enrich_development(dev), realization=realization)


def _played(state: Any) -> list[Any]:
    return _cards(state, "scoring_cards", "played_cards", "current_played_cards")


def realize_aces(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    hits = sum(1 for c in played if _rank(c) == "A")
    payoff = _has(_jokers(state), "scholar", "fibonacci")
    return _finish(dev, bool(hits and payoff), hits >= 3 and payoff)


def realize_face_cards(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    hits = sum(1 for c in played if _rank(c) in {"J", "Q", "K"})
    payoff = _has(_jokers(state), "pareidolia", "sockandbuskin", "photograph", "scaryface", "smileyface", "businesscard")
    return _finish(dev, bool(hits and payoff), hits >= 3 and payoff)


def realize_low_ranks(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    hits = sum(1 for c in played if _rank(c) in {"2", "3", "4", "5"})
    payoff = _has(_jokers(state), "hack", "weejoker", "fibonacci", "evensteven", "walkietalkie")
    return _finish(dev, bool(hits and payoff), hits >= 3 and payoff)


def realize_jacks(dev: BondDevelopment, state: Any) -> BondDevelopment:
    # Hit the Road realizes through discarding Jacks, not scoring them.
    discarded = _cards(state, "discarded_cards", "current_discard_cards")
    jacks = sum(1 for c in discarded if _rank(c) == "J")
    payoff = _has(_jokers(state), "hittheroad")
    return _finish(dev, bool(jacks and payoff), jacks >= 3 and payoff)


def realize_no_face_cards(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    if not played:
        return _finish(dev, False)
    payoff = _has(_jokers(state), "ridethebus")
    no_faces = all(_rank(c) not in {"J", "Q", "K"} for c in played)
    streak = int(getattr(state, "ride_the_bus_streak", 0) or 0)
    return _finish(dev, payoff and no_faces, payoff and no_faces and streak >= 8)


def _realize_suit(dev: BondDevelopment, state: Any, suit: str, *payoffs: str) -> BondDevelopment:
    played = _played(state)
    hits = sum(1 for c in played if _suit(c) == suit)
    payoff = _has(_jokers(state), *payoffs)
    return _finish(dev, bool(hits and payoff), hits >= 4 and payoff)


def realize_hearts(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return _realize_suit(dev, state, "hearts", "bloodstone", "lustyjoker")


def realize_spades(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return _realize_suit(dev, state, "spades", "arrowhead", "wrathfuljoker")


def realize_clubs(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return _realize_suit(dev, state, "clubs", "onyxagate", "gluttonousjoker")


def realize_diamonds(dev: BondDevelopment, state: Any) -> BondDevelopment:
    return _realize_suit(dev, state, "diamonds", "roughgem", "greedyjoker")


def realize_lucky(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    lucky = sum(1 for c in played if _enh(c) == "lucky")
    payoff = _has(_jokers(state), "luckycat", "oopsall6s")
    return _finish(dev, bool(lucky), lucky >= 3 and payoff)


def realize_glass(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    glass = sum(1 for c in played if _enh(c) == "glass")
    payoff = _has(_jokers(state), "glassjoker")
    return _finish(dev, bool(glass), glass >= 2 and payoff)


def realize_stone(dev: BondDevelopment, state: Any) -> BondDevelopment:
    played = _played(state)
    stone = sum(1 for c in played if _enh(c) == "stone" or bool(getattr(c, "is_stone", False)))
    payoff = _has(_jokers(state), "stonejoker", "marblejoker")
    return _finish(dev, bool(stone), stone >= 3 and payoff)


def realize_gold_economy(dev: BondDevelopment, state: Any) -> BondDevelopment:
    hand = _cards(state, "hand", "current_hand", "cards_in_hand")
    gold = sum(1 for c in hand if _enh(c) == "gold")
    payoff = _has(_jokers(state), "goldenticket", "midasmask", "reservedparking")
    # Gold itself realizes at end of round by being held; payoff Jokers strengthen maturity.
    return _finish(dev, bool(gold), gold >= 3 and payoff)


RANK_STATE_REALIZERS = {
    "aces": realize_aces,
    "face_cards": realize_face_cards,
    "low_ranks": realize_low_ranks,
    "jacks": realize_jacks,
    "no_face_cards": realize_no_face_cards,
    "hearts": realize_hearts,
    "spades": realize_spades,
    "clubs": realize_clubs,
    "diamonds": realize_diamonds,
    "lucky": realize_lucky,
    "glass": realize_glass,
    "stone": realize_stone,
    "gold_economy": realize_gold_economy,
}


def realize_rank_state_family(dev: BondDevelopment, state: Any) -> BondDevelopment:
    fn = RANK_STATE_REALIZERS.get(dev.bond_id)
    return fn(dev, state) if fn else enrich_development(dev)
