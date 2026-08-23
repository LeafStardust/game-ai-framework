from __future__ import annotations

"""Semantic face-card Bond bridge for Pareidolia-enabled payoff structures.

Pareidolia is not merely another face-card component: it changes every played card
into a face card for face-card payoffs. Pairing it with Scary Face, Smiley Face,
Photograph, Sock and Buskin, or Business Card therefore creates a mechanically
meaningful enabling relationship that must survive D2/Bond pivot reasoning.
"""

from dataclasses import replace

from games.balatro.bonds.catalogue_batch_one import FACE_CARDS_THRESHOLDS
from games.balatro.bonds.evaluation import EVALUATORS
from games.balatro.bonds.model import BondContribution, BondRank, MechanicalRole


def _token(value: object) -> str:
    raw = getattr(value, "name", None) or type(value).__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has(jokers: tuple[object, ...], *needles: str) -> bool:
    tokens = tuple(_token(joker) for joker in jokers)
    return any(any(needle in token for needle in needles) for token in tokens)


def _rank(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = float(FACE_CARDS_THRESHOLDS[candidate])
        if total >= threshold:
            rank = candidate
        else:
            return rank, threshold
    return BondRank.R5, None


def install_face_card_enabler_bond_policy() -> None:
    original = EVALUATORS.get("face_cards")
    if original is None or getattr(original, "_pareidolia_bridge_installed", False):
        return

    def evaluate(state):
        development = original(state)
        jokers = tuple(getattr(state, "jokers", ()) or ())
        if not _has(jokers, "pareidolia"):
            return development

        payoff_present = _has(
            jokers,
            "scaryface",
            "smileyface",
            "photograph",
            "sockandbuskin",
            "businesscard",
        )
        if not payoff_present:
            return development

        # Semantic mechanic value, not a tunable coefficient: Pareidolia turns the
        # whole deck into valid face-card inputs for an owned payoff/retrigger.
        bridge = BondContribution(
            "Pareidolia all-card face enabler bridge",
            4.0,
            roles=(MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.SUPPORT),
            targets=("J/Q/K",),
            conditions=("Pareidolia owned with at least one face-card payoff",),
        )
        total = float(development.contribution) + bridge.value
        rank, next_threshold = _rank(total)
        return replace(
            development,
            contribution=total,
            rank=rank,
            next_rank_threshold=next_threshold,
            contributions=(*development.contributions, bridge),
        )

    evaluate._pareidolia_bridge_installed = True
    EVALUATORS["face_cards"] = evaluate
