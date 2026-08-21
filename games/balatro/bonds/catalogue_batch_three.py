from __future__ import annotations

from typing import Any, Iterable

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = getattr(value, "name", None)
        if raw is None:
            raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _contains(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    out = 0.0
    for threshold, score in bands:
        if value >= threshold:
            out = score
        else:
            break
    return out


def _level(state: Any, hand: str) -> int:
    return int((getattr(state, "hand_levels", {}) or {}).get(hand, 1) or 1)


def _level_score(level: int) -> float:
    return _band(level, ((2, 1.0), (4, 3.0), (7, 5.0), (11, 7.0)))


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        if total >= thresholds[candidate]:
            rank = candidate
        else:
            return rank, thresholds[candidate]
    return BondRank.R5, None


def _finish(bond_id: str, parts: list[BondContribution], thresholds: dict[BondRank, float], *, target: str | None = None) -> BondDevelopment:
    total = sum(p.value for p in parts)
    rank, next_threshold = _rank(total, thresholds)
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        target=target,
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


def _joker_parts(jokers: list[Any], specs: tuple[tuple[str, float, tuple[str, ...]], ...]) -> list[BondContribution]:
    parts: list[BondContribution] = []
    for label, value, tokens in specs:
        if _contains(jokers, *tokens):
            parts.append(BondContribution(label, value))
    return parts


HAND_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 13.0, BondRank.R4: 19.0, BondRank.R5: 26.0}
SUIT_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0, BondRank.R4: 22.0, BondRank.R5: 30.0}


def _hand_bond(state: Any, bond_id: str, hand: str, specs: tuple[tuple[str, float, tuple[str, ...]], ...] = ()) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, specs)
    score = _level_score(_level(state, hand))
    if score:
        parts.append(BondContribution(f"{hand} permanent hand level", score))
    return _finish(bond_id, parts, HAND_THRESHOLDS, target=hand)


def _suit_bond(state: Any, bond_id: str, suit: str, specs: tuple[tuple[str, float, tuple[str, ...]], ...]) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, specs)
    count = sum(
        1 for card in _deck(state)
        if str(getattr(card, "suit", "") or "").lower() == suit.lower()
        and str(getattr(card, "enhancement", "") or "").lower() != "stone"
    )
    density = _band(count, ((13, 1.0), (17, 3.0), (21, 5.0), (26, 7.0), (32, 9.0)))
    if density:
        parts.append(BondContribution(f"{suit} density", density))
    return _finish(bond_id, parts, SUIT_THRESHOLDS, target=suit.upper())


# 23. Full House
FULL_HOUSE_THRESHOLDS = HAND_THRESHOLDS
FULL_HOUSE_POLICIES = {r: (p,) for r, p in (
    (BondRank.R1, "recognize_full_house_specialization"),
    (BondRank.R2, "prefer_pair_plus_trips_consistency"),
    (BondRank.R3, "actively_shape_rank_structure_for_full_house"),
    (BondRank.R4, "eligible_as_power_engine"),
    (BondRank.R5, "capstone_full_house_commitment"),
)}

def evaluate_full_house_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "full_house", "FULL_HOUSE", (
        ("The Duo", 2.0, ("theduo",)),
        ("The Trio", 2.0, ("thetrio",)),
    ))


# 24. Straight Flush
STRAIGHT_FLUSH_THRESHOLDS = HAND_THRESHOLDS
STRAIGHT_FLUSH_POLICIES = {r: (p,) for r, p in (
    (BondRank.R1, "recognize_straight_flush_specialization"),
    (BondRank.R2, "prefer_joint_straight_and_suit_consistency"),
    (BondRank.R3, "actively_shape_deck_for_straight_flush"),
    (BondRank.R4, "eligible_as_power_engine"),
    (BondRank.R5, "capstone_straight_flush_commitment"),
)}

def evaluate_straight_flush_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "straight_flush", "STRAIGHT_FLUSH", (
        ("Four Fingers", 4.0, ("fourfingers",)),
        ("Shortcut", 3.0, ("shortcut",)),
        ("Smeared Joker", 3.0, ("smearedjoker",)),
    ))


# 25. Five of a Kind
FIVE_KIND_THRESHOLDS = HAND_THRESHOLDS
FIVE_KIND_POLICIES = {r: (p,) for r, p in (
    (BondRank.R1, "recognize_five_kind_specialization"),
    (BondRank.R2, "prefer_extreme_rank_concentration"),
    (BondRank.R3, "actively_shape_deck_for_five_kind"),
    (BondRank.R4, "eligible_as_power_engine"),
    (BondRank.R5, "capstone_five_kind_commitment"),
)}

def evaluate_five_kind_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, (("DNA", 4.0, ("dnajoker", "dna")),))
    ranks: dict[str, int] = {}
    for card in _deck(state):
        rank = str(getattr(card, "rank", "") or "")
        if rank and str(getattr(card, "enhancement", "") or "").lower() != "stone":
            ranks[rank] = ranks.get(rank, 0) + 1
    concentration = _band(max(ranks.values(), default=0), ((5, 2.0), (7, 4.0), (10, 6.0), (14, 8.0)))
    if concentration:
        parts.append(BondContribution("Maximum rank concentration", concentration))
    lvl = _level_score(_level(state, "FIVE_OF_A_KIND"))
    if lvl:
        parts.append(BondContribution("FIVE_OF_A_KIND permanent hand level", lvl))
    return _finish("five_kind", parts, FIVE_KIND_THRESHOLDS, target="FIVE_OF_A_KIND")


# 26. Flush House
FLUSH_HOUSE_THRESHOLDS = HAND_THRESHOLDS
FLUSH_HOUSE_POLICIES = {r: (p,) for r, p in (
    (BondRank.R1, "recognize_flush_house_specialization"),
    (BondRank.R2, "prefer_suited_pair_plus_trips_structure"),
    (BondRank.R3, "actively_shape_deck_for_flush_house"),
    (BondRank.R4, "eligible_as_power_engine"),
    (BondRank.R5, "capstone_flush_house_commitment"),
)}

def evaluate_flush_house_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "flush_house", "FLUSH_HOUSE", (
        ("Smeared Joker", 3.0, ("smearedjoker",)),
        ("The Duo", 1.0, ("theduo",)),
        ("The Trio", 1.0, ("thetrio",)),
    ))


# 27. Flush Five
FLUSH_FIVE_THRESHOLDS = HAND_THRESHOLDS
FLUSH_FIVE_POLICIES = {r: (p,) for r, p in (
    (BondRank.R1, "recognize_flush_five_specialization"),
    (BondRank.R2, "prefer_same_rank_same_suit_concentration"),
    (BondRank.R3, "actively_shape_deck_for_flush_five"),
    (BondRank.R4, "eligible_as_power_engine"),
    (BondRank.R5, "capstone_flush_five_commitment"),
)}

def evaluate_flush_five_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, (
        ("DNA", 3.0, ("dnajoker", "dna")),
        ("Smeared Joker", 2.0, ("smearedjoker",)),
    ))
    groups: dict[tuple[str, str], int] = {}
    for card in _deck(state):
        if str(getattr(card, "enhancement", "") or "").lower() == "stone":
            continue
        key = (str(getattr(card, "rank", "") or ""), str(getattr(card, "suit", "") or ""))
        if all(key):
            groups[key] = groups.get(key, 0) + 1
    concentration = _band(max(groups.values(), default=0), ((5, 3.0), (7, 5.0), (10, 7.0)))
    if concentration:
        parts.append(BondContribution("Same-rank same-suit concentration", concentration))
    lvl = _level_score(_level(state, "FLUSH_FIVE"))
    if lvl:
        parts.append(BondContribution("FLUSH_FIVE permanent hand level", lvl))
    return _finish("flush_five", parts, FLUSH_FIVE_THRESHOLDS, target="FLUSH_FIVE")


# 28-31. Suit Bonds
HEARTS_THRESHOLDS = SUIT_THRESHOLDS
SPADES_THRESHOLDS = SUIT_THRESHOLDS
CLUBS_THRESHOLDS = SUIT_THRESHOLDS
DIAMONDS_THRESHOLDS = SUIT_THRESHOLDS
HEARTS_POLICIES = {BondRank.R1: ("recognize_hearts_specialization",), BondRank.R2: ("prefer_hearts_density",), BondRank.R3: ("actively_shape_toward_hearts",), BondRank.R4: ("eligible_as_power_engine_support",), BondRank.R5: ("capstone_hearts_commitment",)}
SPADES_POLICIES = {BondRank.R1: ("recognize_spades_specialization",), BondRank.R2: ("prefer_spades_density",), BondRank.R3: ("actively_shape_toward_spades",), BondRank.R4: ("eligible_as_power_engine_support",), BondRank.R5: ("capstone_spades_commitment",)}
CLUBS_POLICIES = {BondRank.R1: ("recognize_clubs_specialization",), BondRank.R2: ("prefer_clubs_density",), BondRank.R3: ("actively_shape_toward_clubs",), BondRank.R4: ("eligible_as_power_engine_support",), BondRank.R5: ("capstone_clubs_commitment",)}
DIAMONDS_POLICIES = {BondRank.R1: ("recognize_diamonds_specialization",), BondRank.R2: ("prefer_diamonds_density",), BondRank.R3: ("actively_shape_toward_diamonds",), BondRank.R4: ("eligible_as_power_engine_support",), BondRank.R5: ("capstone_diamonds_commitment",)}

def evaluate_hearts_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "hearts", "Hearts", (
        ("Bloodstone", 7.0, ("bloodstone",)),
        ("Lusty Joker", 4.0, ("lustyjoker",)),
    ))

def evaluate_spades_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "spades", "Spades", (
        ("Arrowhead", 6.0, ("arrowhead",)),
        ("Wrathful Joker", 4.0, ("wrathfuljoker",)),
    ))

def evaluate_clubs_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "clubs", "Clubs", (
        ("Onyx Agate", 6.0, ("onyxagate",)),
        ("Gluttonous Joker", 4.0, ("gluttonousjoker",)),
    ))

def evaluate_diamonds_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "diamonds", "Diamonds", (
        ("Rough Gem", 6.0, ("roughgem",)),
        ("Greedy Joker", 4.0, ("greedyjoker",)),
    ))


# 32. Low Ranks (2-5)
LOW_RANKS_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0, BondRank.R4: 22.0, BondRank.R5: 30.0}
LOW_RANKS_POLICIES = {
    BondRank.R1: ("recognize_low_rank_payoff",),
    BondRank.R2: ("prefer_2_to_5_density_and_payoff",),
    BondRank.R3: ("actively_shape_deck_toward_low_ranks",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_low_rank_commitment",),
}

def evaluate_low_ranks_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, (
        ("Hack", 6.0, ("hackjoker", "hack")),
        ("Wee Joker", 6.0, ("weejoker",)),
        ("Fibonacci", 5.0, ("fibonaccijoker", "fibonacci")),
        ("Even Steven", 3.0, ("evensteven",)),
        ("Walkie Talkie", 2.0, ("walkietalkie",)),
    ))
    low = sum(1 for c in _deck(state) if str(getattr(c, "rank", "") or "") in {"2", "3", "4", "5"})
    density = _band(low, ((16, 1.0), (20, 3.0), (24, 5.0), (30, 7.0)))
    if density:
        parts.append(BondContribution("2-5 rank density", density))
    return _finish("low_ranks", parts, LOW_RANKS_THRESHOLDS, target="2-5")


BATCH_THREE_EVALUATORS = {
    "full_house": evaluate_full_house_bond,
    "straight_flush": evaluate_straight_flush_bond,
    "five_kind": evaluate_five_kind_bond,
    "flush_house": evaluate_flush_house_bond,
    "flush_five": evaluate_flush_five_bond,
    "hearts": evaluate_hearts_bond,
    "spades": evaluate_spades_bond,
    "clubs": evaluate_clubs_bond,
    "diamonds": evaluate_diamonds_bond,
    "low_ranks": evaluate_low_ranks_bond,
}
