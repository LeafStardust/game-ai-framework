from __future__ import annotations

from typing import Any

from games.balatro.bonds.contributions import (
    component_contribution,
    finalize_development,
    state_contribution,
)
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
from games.balatro.mechanics import HELD_KING_XMULT, HELD_QUEEN_MULT, component_has_mechanic

HELD_CARDS_BOND_ID = "held_cards"
HELD_CARDS_RANK_THRESHOLDS: dict[BondRank, float] = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 19.0,
    BondRank.R5: 26.0,
}
HELD_CARDS_RANK_POLICIES: dict[BondRank, tuple[str, ...]] = {
    BondRank.R1: ("recognize_held_card_payoff", "avoid_needlessly_spending_useful_held_payoff_cards"),
    BondRank.R2: ("prefer_held_card_infrastructure_when_build_compatible", "preserve_useful_held_cards_more_consistently"),
    BondRank.R3: ("actively_shape_hand_and_deck_toward_held_payoff", "protect_material_held_card_contributors", "increase_value_of_held_retrigger_and_steel_synergy"),
    BondRank.R4: ("eligible_as_power_engine", "strongly_prioritize_hand_size_and_held_payoff_efficiency", "actively_seek_compatible_held_card_motifs"),
    BondRank.R5: ("capstone_held_card_commitment", "aggressively_optimize_compatible_build_around_held_value", "abandon_only_for_survival_or_clearly_superior_composition"),
}

HELD_LOWEST_RANK_MULT = "held_lowest_rank_mult"
HELD_BLACK_SUIT_XMULT = "held_black_suit_xmult"


def _normalize_name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has_held_mechanic(component: Any, mechanic: str) -> bool:
    if component_has_mechanic(component, mechanic):
        return True
    # Temporary snapshot compatibility for the two held-card components that do
    # not yet expose native mechanics in the shared component descriptor table.
    legacy = {
        "raisedfist": HELD_LOWEST_RANK_MULT,
        "raisedfistjoker": HELD_LOWEST_RANK_MULT,
        "blackboard": HELD_BLACK_SUIT_XMULT,
        "blackboardjoker": HELD_BLACK_SUIT_XMULT,
    }
    return legacy.get(_normalize_name(component)) == mechanic


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    return list(owned) if owned is not None else list(getattr(state, "deck", ()) or ())


def _band(count: int, bands: tuple[tuple[int, float], ...]) -> float:
    value = 0.0
    for threshold, score in bands:
        if count < threshold:
            break
        value = score
    return value


def _source_label(component: Any, fallback: str) -> str:
    raw = getattr(component, "name", None)
    if raw:
        return str(raw)
    class_name = component.__class__.__name__
    return class_name if class_name not in {"str", "SimpleNamespace"} else fallback


def evaluate_held_cards_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []
    weights = (
        (HELD_KING_XMULT, 6.0, "Held King XMult"),
        (HELD_QUEEN_MULT, 4.0, "Held Queen Mult"),
        (HELD_LOWEST_RANK_MULT, 2.0, "Held lowest-rank Mult"),
        (HELD_BLACK_SUIT_XMULT, 4.0, "Held black-suit XMult"),
    )
    for index, joker in enumerate(jokers):
        for mechanic, value, label in weights:
            if _has_held_mechanic(joker, mechanic):
                parts.append(component_contribution(
                    joker,
                    collection="jokers",
                    index=index,
                    label=_source_label(joker, label),
                    value=value,
                    mechanic=mechanic,
                ))

    steel = _band(
        sum(1 for card in _owned_deck(state) if str(getattr(card, "enhancement", "") or "").strip().lower() == "steel"),
        ((1, 1.0), (2, 3.0), (4, 5.0), (6, 7.0)),
    )
    if steel:
        parts.append(state_contribution(
            "deck:steel_held_density",
            "Steel held-card infrastructure",
            steel,
            mechanic="steel_held_density",
        ))

    hand_size = float(min(3, max(0, int(getattr(state, "hand_size", 8) or 8) - 8)))
    if hand_size:
        parts.append(state_contribution(
            "hand:extra_size",
            "Extra hand size",
            hand_size,
            mechanic="extra_hand_size",
        ))

    return finalize_development(
        HELD_CARDS_BOND_ID,
        parts,
        HELD_CARDS_RANK_THRESHOLDS,
    )
