from __future__ import annotations

from typing import Any

from games.balatro.bonds.contributions import component_contribution, finalize_development, state_contribution
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
from games.balatro.mechanics_compat import NO_FACE_PLAY_SCALING, component_has_public_mechanic


NO_FACE_CARDS_BOND_ID = "no_face_cards"
NO_FACE_CARDS_RANK_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 10.0,
    BondRank.R4: 12.0,
    BondRank.R5: 14.0,
}
NO_FACE_CARDS_RANK_POLICIES = {
    BondRank.R1: ("recognize_ride_the_bus_no_face_payoff",),
    BondRank.R2: ("prefer_lines_that_do_not_score_face_cards",),
    BondRank.R3: ("actively_reduce_face_card_interference",),
    BondRank.R4: ("eligible_as_power_engine_when_bus_scaling_is_realized",),
    BondRank.R5: ("capstone_face_free_commitment",),
}


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _source(component: Any) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    cls = component.__class__.__name__
    return "No-face play scaler" if cls in {"str", "SimpleNamespace"} else cls


def _locked() -> BondDevelopment:
    return BondDevelopment(
        bond_id=NO_FACE_CARDS_BOND_ID,
        unlocked=False,
        contribution=0.0,
        rank=BondRank.LOCKED,
        next_rank_threshold=NO_FACE_CARDS_RANK_THRESHOLDS[BondRank.R1],
        contributions=(),
        target="NO_FACE_CARDS",
    )


def evaluate_no_face_cards_bond(state: Any) -> BondDevelopment:
    """Evaluate no-face development from an explicit no-face scaling mechanic."""
    jokers = list(getattr(state, "jokers", ()) or ())
    scaler_index = next(
        (
            index
            for index, joker in enumerate(jokers)
            if component_has_public_mechanic(joker, NO_FACE_PLAY_SCALING)
        ),
        None,
    )
    if scaler_index is None:
        return _locked()

    scaler = jokers[scaler_index]
    parts: list[BondContribution] = [
        component_contribution(
            scaler,
            collection="jokers",
            index=scaler_index,
            label=_source(scaler),
            value=7.0,
            mechanic=NO_FACE_PLAY_SCALING,
        )
    ]
    deck = _deck(state)

    if deck:
        face_count = sum(
            1
            for card in deck
            if str(getattr(card, "rank", "") or "").upper() in {"J", "Q", "K"}
            and str(getattr(card, "enhancement", "") or "").lower() != "stone"
        )

        density_score = 0.0
        if face_count == 0:
            density_score = 7.0
        elif face_count <= 3:
            density_score = 5.0
        elif face_count <= 6:
            density_score = 3.0
        elif face_count <= 9:
            density_score = 1.0

        if density_score:
            parts.append(state_contribution(
                "deck:natural_face_density",
                "Low natural face-card density",
                density_score,
                mechanic="natural_face_card_density",
            ))

    return finalize_development(
        NO_FACE_CARDS_BOND_ID,
        parts,
        NO_FACE_CARDS_RANK_THRESHOLDS,
        target="NO_FACE_CARDS",
    )


NO_FACE_CARDS_RELATIONSHIPS = {
    frozenset(("face_cards", "no_face_cards")): "CONFLICT",
}
