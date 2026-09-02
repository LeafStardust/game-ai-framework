from __future__ import annotations

from games.balatro.bonds.mechanical_roles import ROLE_REGISTRY
from games.balatro.bonds.rank_progression import canonical_rank_thresholds
from games.balatro.bonds.semantic_coverage import (
    BEHAVIOR_FEATURE_BONDS,
    DEDICATED_SEMANTIC_BONDS,
    audit_semantic_coverage,
    uncovered_bonds,
)


def test_every_frozen_bond_has_a_strategy_semantic_channel() -> None:
    thresholds = canonical_rank_thresholds()
    coverage = audit_semantic_coverage()

    assert len(thresholds) == 46
    assert set(coverage) == set(thresholds)
    assert uncovered_bonds() == ()


def test_behavior_feature_mapping_covers_core_build_axes() -> None:
    expected = {
        "kings", "queens", "steel", "held_cards", "held_retrigger",
        "played_retrigger", "cash", "gold_cards", "enhanced_cards",
        "straight", "flush", "full_house", "low_ranks",
    }
    assert expected <= BEHAVIOR_FEATURE_BONDS


def test_non_feature_axes_are_explicitly_owned_by_dedicated_semantics() -> None:
    expected = {
        "hand_leveling", "blind_skip", "card_destruction", "deck_growth", "discard",
        "hand_repetition", "joker_sacrifice", "no_discard", "no_face_cards",
        "planet", "sell_value", "stone", "tarot", "enhancement_consumption",
    }
    assert expected <= DEDICATED_SEMANTIC_BONDS


def test_explicit_role_registry_contains_known_cross_mechanic_enablers() -> None:
    assert "Baron" in ROLE_REGISTRY
    assert "Mime" in ROLE_REGISTRY
    assert "Steel held-card infrastructure" in ROLE_REGISTRY
    assert "Midas Mask" in ROLE_REGISTRY
    assert "Vampire" in ROLE_REGISTRY
    assert "Trading Card" in ROLE_REGISTRY
    assert "Erosion" in ROLE_REGISTRY
