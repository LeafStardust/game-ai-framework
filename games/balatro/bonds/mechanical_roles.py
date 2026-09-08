from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from games.balatro.bonds.model import BondContribution, BondDevelopment, MechanicalRole


ROLE_REGISTRY: dict[str, dict[str, tuple]] = {
    "Baron": {"roles": (MechanicalRole.HELD_RANK_PAYOFF, MechanicalRole.RANK_PAYOFF), "targets": ("KINGS",), "conditions": ("CARD_HELD_IN_HAND",)},
    "Mime": {"roles": (MechanicalRole.HELD_RETRIGGER,), "targets": ("HELD_CARD_EFFECTS",), "conditions": ("HELD_EFFECT_PRESENT",)},
    "Blackboard": {"roles": (MechanicalRole.HELD_STATE_PAYOFF,), "targets": ("HELD_BLACK_SUITS",), "conditions": ("ALL_REMAINING_HELD_CARDS_SPADES_OR_CLUBS",)},
    "Shoot the Moon": {"roles": (MechanicalRole.HELD_RANK_PAYOFF, MechanicalRole.RANK_PAYOFF), "targets": ("QUEENS",), "conditions": ("CARD_HELD_IN_HAND",)},
    "Raised Fist": {"roles": (MechanicalRole.HELD_RANK_PAYOFF,), "targets": ("LOWEST_HELD_RANK",), "conditions": ("CARD_HELD_IN_HAND",)},
    "Steel held-card infrastructure": {"roles": (MechanicalRole.HELD_CARD_XMULT, MechanicalRole.DENSITY_INFRASTRUCTURE), "targets": ("STEEL_CARDS",), "conditions": ("STEEL_CARD_HELD_IN_HAND",)},
    "Steel Joker": {"roles": (MechanicalRole.ENHANCEMENT_PAYOFF, MechanicalRole.SCALER), "targets": ("STEEL_CARDS",)},
    "Erosion": {"roles": (MechanicalRole.DECK_THIN_PAYOFF,), "targets": ("REDUCED_DECK_SIZE",)},
    "Trading Card": {"roles": (MechanicalRole.DECK_THIN_ENGINE,), "targets": ("PLAYING_CARDS",)},
    "Sixth Sense": {"roles": (MechanicalRole.DECK_THIN_ENGINE, MechanicalRole.CONSUMABLE_ENGINE), "targets": ("SIXES", "SPECTRAL")},
    "Square Joker": {"roles": (MechanicalRole.HAND_PAYOFF, MechanicalRole.SCALER), "targets": ("FOUR_CARD_HANDS",), "conditions": ("EXACTLY_FOUR_CARDS_PLAYED",)},
    "Spare Trousers": {"roles": (MechanicalRole.HAND_PAYOFF, MechanicalRole.SCALER), "targets": ("TWO_PAIR",)},
    "Stuntman": {"roles": (MechanicalRole.HAND_PAYOFF,), "targets": ("HIGH_CARD",), "conditions": ("HAND_SIZE_PENALTY_ACCEPTABLE",)},
    "Superposition": {"roles": (MechanicalRole.CONSUMABLE_ENGINE, MechanicalRole.SUPPORT), "targets": ("STRAIGHT", "TAROT"), "conditions": ("STRAIGHT_CONTAINS_ACE",)},
    "Ancient Joker": {"roles": (MechanicalRole.SUIT_PAYOFF,), "targets": ("ROTATING_SUIT", "FLUSH"), "conditions": ("SCORING_CARD_MATCHES_CURRENT_ANCIENT_SUIT",)},
    "Cloud 9": {"roles": (MechanicalRole.ECONOMY_ENGINE, MechanicalRole.RANK_PAYOFF), "targets": ("NINES", "CASH")},
    "8 Ball": {"roles": (MechanicalRole.CONSUMABLE_ENGINE,), "targets": ("EIGHTS", "TAROT"), "conditions": ("SCORING_EIGHT_TRIGGERS",)},
    "Vampire": {"roles": (MechanicalRole.ENHANCEMENT_PAYOFF, MechanicalRole.SCALER), "targets": ("ENHANCED_SCORING_CARDS",), "conditions": ("CONSUMES_ENHANCEMENTS",)},
    "Midas Mask": {"roles": (MechanicalRole.ENHANCEMENT_FEED,), "targets": ("GOLD_FACE_CARDS", "VAMPIRE_FEED")},
    "Driver's License": {"roles": (MechanicalRole.ENHANCEMENT_PAYOFF,), "targets": ("ENHANCED_CARD_DENSITY",), "conditions": ("PRESERVE_ENHANCEMENTS",)},
    "Blueprint copying Mime potential": {"roles": (MechanicalRole.COPY_ENGINE, MechanicalRole.HELD_RETRIGGER), "targets": ("MIME",)},
    "Brainstorm copying Mime potential": {"roles": (MechanicalRole.COPY_ENGINE, MechanicalRole.HELD_RETRIGGER), "targets": ("MIME",)},
}


def enrich_contribution(contribution: BondContribution) -> BondContribution:
    metadata = ROLE_REGISTRY.get(contribution.source)
    if not metadata:
        return contribution
    return replace(
        contribution,
        roles=tuple(metadata.get("roles", ())),
        targets=tuple(metadata.get("targets", ())),
        conditions=tuple(metadata.get("conditions", ())),
    )


def enrich_contributions(contributions: Iterable[BondContribution]) -> tuple[BondContribution, ...]:
    return tuple(enrich_contribution(c) for c in contributions)


def enrich_development(development: BondDevelopment) -> BondDevelopment:
    """Return the same Bond development/rank with mechanical metadata attached.

    This transformation is intentionally quota-neutral: contribution totals,
    rank, target and realization are unchanged.
    """
    return replace(development, contributions=enrich_contributions(development.contributions))
