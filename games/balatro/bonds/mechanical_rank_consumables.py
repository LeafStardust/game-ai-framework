from __future__ import annotations

from typing import Any

from games.balatro.bonds.contributions import component_contribution, finalize_development, state_contribution
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
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
    PROBABILISTIC_HAND_LEVELING,
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


def _rank_bond(state: Any, bond_id: str, target: str, weights: tuple[tuple[str, float, str], ...]) -> BondDevelopment:
    parts: list[BondContribution] = []
    jokers = list(getattr(state, "jokers", ()) or ())
    for index, joker in enumerate(jokers):
        for mechanic, value, fallback in weights:
            if component_has_mechanic(joker, mechanic):
                parts.append(component_contribution(
                    joker, collection="jokers", index=index,
                    label=_source(joker, fallback), value=value, mechanic=mechanic,
                ))
                break
    density = _rank_density(state, {target})
    if density:
        parts.append(state_contribution(
            f"deck:rank_density:{target}", f"{bond_id} rank density", density,
            mechanic=f"rank_density:{target}",
        ))
    return finalize_development(bond_id, parts, RANK_THRESHOLDS, target=target)


def evaluate_kings_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "kings", "K", (
        (HELD_KING_XMULT, 7.0, "Held-King payoff"),
        (PLAYED_KING_QUEEN_XMULT, 6.0, "Played K/Q payoff"),
    ))


def evaluate_queens_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "queens", "Q", (
        (HELD_QUEEN_MULT, 6.0, "Held-Queen payoff"),
        (PLAYED_KING_QUEEN_XMULT, 5.0, "Played K/Q payoff"),
    ))


def evaluate_jacks_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "jacks", "J", (
        (DISCARD_JACK_XMULT, 7.0, "Jack-discard payoff"),
    ))


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
    for index, component in enumerate(list(getattr(state, "jokers", ()) or ())):
        for mechanic, value, fallback in weighted:
            if component_has_mechanic(component, mechanic):
                parts.append(component_contribution(
                    component, collection="jokers", index=index,
                    label=_source(component, fallback), value=value, mechanic=mechanic,
                ))
                break
    for index, component in enumerate(list(getattr(state, "vouchers", ()) or ())):
        if component_has_mechanic(component, TAROT_SHOP_ACCESS_MAJOR):
            mechanic, value, fallback = TAROT_SHOP_ACCESS_MAJOR, 6.0, "Major Tarot shop access"
        elif component_has_mechanic(component, TAROT_SHOP_ACCESS):
            mechanic, value, fallback = TAROT_SHOP_ACCESS, 4.0, "Tarot shop access"
        else:
            continue
        parts.append(component_contribution(
            component, collection="vouchers", index=index,
            label=_source(component, fallback), value=value, mechanic=mechanic,
        ))
    return finalize_development("tarot", parts, TAROT_THRESHOLDS)


def evaluate_planet_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for index, component in enumerate(list(getattr(state, "jokers", ()) or ())):
        if component_has_mechanic(component, PLANET_SCALING):
            mechanic, value, fallback = PLANET_SCALING, 6.0, "Planet-use scaling"
        elif component_has_mechanic(component, PLANET_GENERATION):
            mechanic = PLANET_GENERATION
            value = 3.0 if component_has_mechanic(component, PROBABILISTIC_HAND_LEVELING) else 4.0
            fallback = "Planet generation"
        else:
            continue
        parts.append(component_contribution(
            component, collection="jokers", index=index,
            label=_source(component, fallback), value=value, mechanic=mechanic,
        ))
    for index, component in enumerate(list(getattr(state, "vouchers", ()) or ())):
        if component_has_mechanic(component, PLANET_PACK_TARGETING):
            mechanic, value, fallback = PLANET_PACK_TARGETING, 5.0, "Planet pack targeting"
        elif component_has_mechanic(component, PLANET_SHOP_ACCESS_MAJOR):
            mechanic, value, fallback = PLANET_SHOP_ACCESS_MAJOR, 6.0, "Major Planet shop access"
        elif component_has_mechanic(component, PLANET_SHOP_ACCESS):
            mechanic, value, fallback = PLANET_SHOP_ACCESS, 4.0, "Planet shop access"
        else:
            continue
        parts.append(component_contribution(
            component, collection="vouchers", index=index,
            label=_source(component, fallback), value=value, mechanic=mechanic,
        ))

    blue_seals = sum(
        1 for card in _deck(state)
        if str(getattr(card, "seal", "") or "").strip().lower() == "blue"
    )
    blue_score = _band(blue_seals, ((1, 1.0), (2, 3.0), (4, 5.0), (7, 7.0)))
    if blue_score:
        parts.append(state_contribution(
            "deck:blue_seal_density", "Blue Seal Planet infrastructure", blue_score,
            mechanic="blue_seal_density",
        ))
    return finalize_development("planet", parts, PLANET_THRESHOLDS)


MECHANICAL_RANK_CONSUMABLE_EVALUATORS = {
    "kings": evaluate_kings_bond,
    "queens": evaluate_queens_bond,
    "jacks": evaluate_jacks_bond,
    "tarot": evaluate_tarot_bond,
    "planet": evaluate_planet_bond,
}
