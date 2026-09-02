from __future__ import annotations

"""Static audit for the Bond system's mechanical vocabulary.

Rank reachability is not enough: a Bond that never exposes roles/targets and is not
mapped from behavior features is strategically opaque. This module makes that
coverage measurable across the frozen catalogue.
"""

from dataclasses import dataclass

from games.balatro.bonds.mechanical_roles import ROLE_REGISTRY
from games.balatro.bonds.rank_progression import canonical_rank_thresholds


# Bonds that the behavior profiler can map directly from generic feature tokens.
BEHAVIOR_FEATURE_BONDS = frozenset({
    "aces", "cash", "clubs", "diamonds", "enhanced_cards", "flush", "flush_five",
    "flush_house", "four_kind", "glass", "gold_cards", "hearts", "held_cards",
    "held_retrigger", "high_card", "jacks", "kings", "low_ranks", "pair",
    "played_retrigger", "queens", "spades", "steel", "straight", "straight_flush",
    "three_kind", "two_pair", "five_kind", "full_house",
})

# Strategy axes whose semantics are intentionally supplied by dedicated evaluators
# or other axis-specific mechanics rather than generic behavior feature tokens.
DEDICATED_SEMANTIC_BONDS = frozenset({
    "blind_skip", "hand_leveling", "card_destruction", "deck_growth", "deck_thinning",
    "discard", "hand_repetition", "joker_sacrifice", "lucky", "no_discard",
    "no_face_cards", "planet", "sell_value", "stone", "tarot",
    "enhancement_consumption", "face_cards",
})


@dataclass(frozen=True)
class SemanticCoverage:
    bond_id: str
    explicit_sources: tuple[str, ...]
    behavior_feature: bool
    dedicated_semantics: bool

    @property
    def covered(self) -> bool:
        return bool(self.explicit_sources) or self.behavior_feature or self.dedicated_semantics


def explicit_role_sources_by_bond() -> dict[str, set[str]]:
    """Infer Bond ownership of explicit role sources from their mechanical targets.

    This is deliberately conservative: it is diagnostic metadata, not runtime
    strategy logic. Runtime role enrichment remains source-based.
    """
    mapping: dict[str, set[str]] = {bond_id: set() for bond_id in canonical_rank_thresholds()}
    target_hints = {
        "kings": {"KINGS"}, "queens": {"QUEENS"}, "steel": {"STEEL_CARDS"},
        "cash": {"CASH"}, "straight": {"STRAIGHT"}, "low_ranks": {"LOWEST_HELD_RANK"},
        "enhanced_cards": {"ENHANCED_CARD_DENSITY", "ENHANCED_SCORING_CARDS"},
        "held_cards": {"HELD_CARD_EFFECTS", "HELD_BLACK_SUITS", "STEEL_CARDS"},
        "held_retrigger": {"HELD_CARD_EFFECTS", "MIME"},
        "deck_thinning": {"PLAYING_CARDS", "REDUCED_DECK_SIZE"},
        "tarot": {"TAROT"},
        "enhancement_consumption": {"VAMPIRE_FEED", "ENHANCED_SCORING_CARDS"},
    }
    for source, metadata in ROLE_REGISTRY.items():
        targets = {str(target) for target in metadata.get("targets", ())}
        for bond_id, hints in target_hints.items():
            if targets.intersection(hints):
                mapping.setdefault(bond_id, set()).add(source)
    return mapping


def audit_semantic_coverage() -> dict[str, SemanticCoverage]:
    role_sources = explicit_role_sources_by_bond()
    return {
        bond_id: SemanticCoverage(
            bond_id=bond_id,
            explicit_sources=tuple(sorted(role_sources.get(bond_id, ()))),
            behavior_feature=bond_id in BEHAVIOR_FEATURE_BONDS,
            dedicated_semantics=bond_id in DEDICATED_SEMANTIC_BONDS,
        )
        for bond_id in canonical_rank_thresholds()
    }


def uncovered_bonds() -> tuple[str, ...]:
    return tuple(sorted(bond_id for bond_id, coverage in audit_semantic_coverage().items() if not coverage.covered))
