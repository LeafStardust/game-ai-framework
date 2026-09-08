from __future__ import annotations

from games.balatro.bonds.ids import BOND_IDS
from games.balatro.bonds.mechanical_roles import ROLE_REGISTRY
from games.balatro.bonds.rank_progression import canonical_rank_thresholds
from games.balatro.bonds.semantic_coverage import (
    BOND_SEMANTIC_REQUIREMENTS,
    assert_catalogue_semantics_are_frozen,
    audit_semantic_coverage,
    semantic_vocabulary,
    uncovered_bonds,
)


def test_every_frozen_bond_has_explicit_public_semantics() -> None:
    thresholds = canonical_rank_thresholds()
    coverage = audit_semantic_coverage()

    assert len(BOND_IDS) == 46
    assert set(thresholds) == set(BOND_IDS)
    assert set(BOND_SEMANTIC_REQUIREMENTS) == set(BOND_IDS)
    assert set(coverage) == set(BOND_IDS)
    assert uncovered_bonds() == ()
    assert all(item.covered for item in coverage.values())
    assert_catalogue_semantics_are_frozen()


def test_semantic_contract_uses_mechanics_and_public_state_not_strategy_commands() -> None:
    vocabulary = semantic_vocabulary()

    assert "discard_hand_leveling" in vocabulary
    assert "retrigger_held_cards" in vocabulary
    assert "card_destruction" in vocabulary
    assert "gold_card_generation" in vocabulary
    assert "enhancement_consumption" in vocabulary
    assert "hand_levels" in vocabulary
    assert "owned_deck_size" in vocabulary

    forbidden_prefixes = ("seek_", "preserve_", "commit_", "pivot_", "protect_")
    assert not any(token.startswith(forbidden_prefixes) for token in vocabulary)


def test_representative_bonds_declare_cross_mechanic_evidence() -> None:
    hand_leveling = BOND_SEMANTIC_REQUIREMENTS["hand_leveling"]
    assert "discard_hand_leveling" in hand_leveling.mechanics
    assert "planet_pack_targeting" in hand_leveling.mechanics
    assert "hand_levels" in hand_leveling.state_features

    held_retrigger = BOND_SEMANTIC_REQUIREMENTS["held_retrigger"]
    assert "retrigger_held_cards" in held_retrigger.mechanics
    assert "copy_effect" in held_retrigger.mechanics
    assert "red_seal_density" in held_retrigger.state_features

    thinning = BOND_SEMANTIC_REQUIREMENTS["deck_thinning"]
    assert "card_destruction" in thinning.mechanics
    assert "deck_thin_payoff" in thinning.mechanics
    assert "owned_deck_size" in thinning.state_features

    consumption = BOND_SEMANTIC_REQUIREMENTS["enhancement_consumption"]
    assert "enhancement_consumption" in consumption.mechanics
    assert "enhancement_feed_access" in consumption.mechanics
    assert "enhanced_card_density" in consumption.state_features


def test_explicit_role_registry_contains_known_cross_mechanic_enablers() -> None:
    assert "Baron" in ROLE_REGISTRY
    assert "Mime" in ROLE_REGISTRY
    assert "Steel held-card infrastructure" in ROLE_REGISTRY
    assert "Midas Mask" in ROLE_REGISTRY
    assert "Vampire" in ROLE_REGISTRY
    assert "Trading Card" in ROLE_REGISTRY
    assert "Erosion" in ROLE_REGISTRY
