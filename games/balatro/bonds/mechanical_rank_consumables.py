from __future__ import annotations

from typing import Any

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.mechanics import (
    DISCARD_JACK_XMULT,
    HELD_KING_XMULT,
    HELD_QUEEN_MULT,
    PLANET_GENERATION,
    PLANET_PACK_TARGETING,
    PLANET_SCALING,
    PLANET_SHOP_ACCESS,
    PLANET_SHOP_ACCESS_MAJOR,
    PLAYED_KING_QUEEN_XMULT,
    TAROT_GENERATION,
    TAROT_LOW_MONEY_GENERATION,
    TAROT_PACK_GENERATION,
    TAROT_SCALING,
    TAROT_SCORING_EIGHT_GENERATION,
    TAROT_SHOP_ACCESS,
    TAROT_SHOP_ACCESS_MAJOR,
    TAROT_STRAIGHT_ACE_GENERATION,
    component_has_mechanic,
)

RANK_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 22.0,
    BondRank.R5: 30.0,
}
TAROT_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 22.0,
    BondRank.R5: 28.0,
}
PLANET_THRESHOLDS = dict(RANK_THRESHOLDS)


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    result = 0.0
    for threshold, score in bands:
        if value < threshold:
            break
        result = score
    return result


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = thresholds[candidate]
        if total < threshold:
            return rank, threshold
        rank = candidate
    return BondRank.R5, None


def _finish(
    bond_id: str,
    parts: list[BondContribution],
    thresholds: dict[BondRank, float],
    *,
    target: str | None = None,
) -> BondDevelopment:
    total = sum(part.value for part in parts)
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


def _source(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    class_name = component.__class__.__name__
    return fallback if class_name in {"str", "SimpleNamespace"} else class_name


def _rank_density(state: Any, ranks: set[str]) -> float:
    count = sum(
        1
        for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").lower() != "stone"
        and str(getattr(card, "rank", "") or "").upper() in ranks
    )
    return _band(
        count,
        ((4, 1.0), (6, 3.0), (9, 5.0), (13, 7.0), (18, 9.0), (24, 13.0), (32, 17.0), (40, 21.0), (44, 23.0)),
    )


def evaluate_kings_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for joker in list(getattr(state, "jokers", ()) or ()):
        if component_has_mechanic(joker, HELD_KING_XMULT):
            parts.append(BondContribution(_source(joker, "Held-King payoff"), 7.0))
        elif component_has_mechanic(joker, PLAYED_KING_QUEEN_XMULT):
            parts.append(BondContribution(_source(joker, "Played K/Q payoff"), 6.0))
    density = _rank_density(state, {"K"})
    if density:
        parts.append(BondContribution("kings rank density", density))
    return _finish("kings", parts, RANK_THRESHOLDS, target="K")


def evaluate_queens_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for joker in list(getattr(state, "jokers", ()) or ()):
        if component_has_mechanic(joker, HELD_QUEEN_MULT):
            parts.append(BondContribution(_source(joker, "Held-Queen payoff"), 6.0))
        elif component_has_mechanic(joker, PLAYED_KING_QUEEN_XMULT):
            parts.append(BondContribution(_source(joker, "Played K/Q payoff"), 5.0))
    density = _rank_density(state, {"Q"})
    if density:
        parts.append(BondContribution("queens rank density", density))
    return _finish("queens", parts, RANK_THRESHOLDS, target="Q")


def evaluate_jacks_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for joker in list(getattr(state, "jokers", ()) or ()):
        if component_has_mechanic(joker, DISCARD_JACK_XMULT):
            parts.append(BondContribution(_source(joker, "Jack-discard payoff"), 7.0))
    density = _rank_density(state, {"J"})
    if density:
        parts.append(BondContribution("jacks rank density", density))
    return _finish("jacks", parts, RANK_THRESHOLDS, target="J")


def evaluate_tarot_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    weighted = (
        (TAROT_GENERATION, 6.0, "Blind-selected Tarot generation"),
        (TAROT_LOW_MONEY_GENERATION, 5.0, "Low-money Tarot generation"),
        (TAROT_PACK_GENERATION, 4.0, "Booster-pack Tarot generation"),
        (TAROT_SCALING, 4.0, "Tarot-use scaling"),
        (TAROT_SCORING_EIGHT_GENERATION, 2.0, "Eight-trigger Tarot generation"),
        (TAROT_STRAIGHT_ACE_GENERATION, 2.0, "Straight-Ace Tarot generation"),
    )
    for component in list(getattr(state, "jokers", ()) or ()):
        for mechanic, value, fallback in weighted:
            if component_has_mechanic(component, mechanic):
                parts.append(BondContribution(_source(component, fallback), value))
                break
    for component in list(getattr(state, "vouchers", ()) or ()):
        if component_has_mechanic(component, TAROT_SHOP_ACCESS_MAJOR):
            parts.append(BondContribution(_source(component, "Major Tarot shop access"), 6.0))
        elif component_has_mechanic(component, TAROT_SHOP_ACCESS):
            parts.append(BondContribution(_source(component, "Tarot shop access"), 4.0))
    return _finish("tarot", parts, TAROT_THRESHOLDS)


def evaluate_planet_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for component in list(getattr(state, "jokers", ()) or ()):
        if component_has_mechanic(component, PLANET_SCALING):
            parts.append(BondContribution(_source(component, "Planet-use scaling"), 6.0))
        elif component_has_mechanic(component, PLANET_GENERATION):
            # Space Joker historically contributes 3 while Astronomer contributes 4.
            value = 3.0 if component_has_mechanic(component, "probabilistic_hand_leveling") else 4.0
            parts.append(BondContribution(_source(component, "Planet generation"), value))
    for component in list(getattr(state, "vouchers", ()) or ()):
        if component_has_mechanic(component, PLANET_PACK_TARGETING):
            parts.append(BondContribution(_source(component, "Planet pack targeting"), 5.0))
        elif component_has_mechanic(component, PLANET_SHOP_ACCESS_MAJOR):
            parts.append(BondContribution(_source(component, "Major Planet shop access"), 6.0))
        elif component_has_mechanic(component, PLANET_SHOP_ACCESS):
            parts.append(BondContribution(_source(component, "Planet shop access"), 4.0))

    blue_seals = sum(
        1 for card in _deck(state)
        if str(getattr(card, "seal", "") or "").strip().lower() == "blue"
    )
    blue_score = _band(blue_seals, ((1, 1.0), (2, 3.0), (4, 5.0), (7, 7.0)))
    if blue_score:
        parts.append(BondContribution("Blue Seal Planet infrastructure", blue_score))
    return _finish("planet", parts, PLANET_THRESHOLDS)


MECHANICAL_RANK_CONSUMABLE_EVALUATORS = {
    "kings": evaluate_kings_bond,
    "queens": evaluate_queens_bond,
    "jacks": evaluate_jacks_bond,
    "tarot": evaluate_tarot_bond,
    "planet": evaluate_planet_bond,
}
