from __future__ import annotations

"""Deterministic audit of public semantics required by the frozen Bond catalogue.

Phase B is about mechanical meaning, not scoring.  Every Bond therefore declares
which public mechanics and/or persistent state features are required to explain
that strategic axis.  This table is intentionally independent from StrategyPlan,
commitment, prescriptions, and rank authority.
"""

from dataclasses import dataclass

from games.balatro.bonds.ids import BOND_IDS
from games.balatro.bonds.mechanical_roles import ROLE_REGISTRY
from games.balatro.bonds.rank_progression import canonical_rank_thresholds


@dataclass(frozen=True)
class SemanticRequirement:
    mechanics: tuple[str, ...] = ()
    state_features: tuple[str, ...] = ()

    @property
    def explained(self) -> bool:
        return bool(self.mechanics or self.state_features)


# Public semantic vocabulary required to explain each retained Bond.  These are
# mechanics/state facts, never candidate actions or strategy commands.
BOND_SEMANTIC_REQUIREMENTS: dict[str, SemanticRequirement] = {
    "hand_leveling": SemanticRequirement(
        mechanics=("discard_hand_leveling", "probabilistic_hand_leveling", "planet_pack_targeting"),
        state_features=("hand_levels", "blue_seal_density", "discard_capacity"),
    ),
    "held_cards": SemanticRequirement(
        mechanics=("held_card_payoff", "held_rank_payoff", "held_state_payoff"),
        state_features=("cards_in_hand", "held_enhancement_density"),
    ),
    "held_retrigger": SemanticRequirement(
        mechanics=("retrigger_held_cards", "copy_effect"),
        state_features=("red_seal_density",),
    ),
    "steel": SemanticRequirement(
        mechanics=("steel_card_payoff",),
        state_features=("steel_card_density", "red_seal_steel_overlap"),
    ),
    "pair": SemanticRequirement(
        mechanics=("pair_payoff",), state_features=("pair_hand_level", "pair_play_history")
    ),
    "high_card": SemanticRequirement(
        mechanics=("high_card_payoff",), state_features=("high_card_hand_level", "high_card_play_history")
    ),
    "aces": SemanticRequirement(
        mechanics=("ace_payoff", "rank_duplication"), state_features=("ace_density",)
    ),
    "no_discard": SemanticRequirement(
        mechanics=("discard_penalty", "no_discard_payoff", "discard_removal"),
        state_features=("discard_capacity",),
    ),
    "cash": SemanticRequirement(
        mechanics=("cash_scaling", "interest_payoff", "economy_generation"),
        state_features=("money",),
    ),
    "lucky": SemanticRequirement(
        mechanics=("lucky_card_payoff", "probability_modifier"), state_features=("lucky_card_density",)
    ),
    "glass": SemanticRequirement(
        mechanics=("glass_card_payoff", "glass_break_scaling"),
        state_features=("glass_card_density", "glass_cards_destroyed"),
    ),
    "face_cards": SemanticRequirement(
        mechanics=("face_card_payoff", "all_cards_are_face"), state_features=("face_card_density",)
    ),
    "two_pair": SemanticRequirement(
        mechanics=("two_pair_payoff",), state_features=("two_pair_hand_level", "two_pair_play_history")
    ),
    "three_kind": SemanticRequirement(
        mechanics=("three_kind_payoff",), state_features=("three_kind_hand_level", "rank_multiplicity")
    ),
    "four_kind": SemanticRequirement(
        mechanics=("four_kind_payoff",), state_features=("four_kind_hand_level", "rank_multiplicity")
    ),
    "straight": SemanticRequirement(
        mechanics=("straight_payoff", "straight_range_modifier"),
        state_features=("straight_hand_level", "rank_connectivity"),
    ),
    "flush": SemanticRequirement(
        mechanics=("flush_payoff",), state_features=("flush_hand_level", "suit_density")
    ),
    "played_retrigger": SemanticRequirement(
        mechanics=("retrigger_played_cards",), state_features=("red_seal_density",)
    ),
    "stone": SemanticRequirement(
        mechanics=("stone_card_payoff",), state_features=("stone_card_density",)
    ),
    "gold_cards": SemanticRequirement(
        mechanics=("gold_card_generation", "gold_card_scoring_economy", "held_face_economy"),
        state_features=("gold_card_density",),
    ),
    "deck_thinning": SemanticRequirement(
        mechanics=("card_destruction", "deck_thin_payoff"), state_features=("owned_deck_size",)
    ),
    "deck_growth": SemanticRequirement(
        mechanics=("card_creation", "rank_duplication"), state_features=("owned_deck_size",)
    ),
    "full_house": SemanticRequirement(
        mechanics=("full_house_payoff",), state_features=("full_house_hand_level", "rank_multiplicity")
    ),
    "straight_flush": SemanticRequirement(
        mechanics=("straight_flush_payoff",),
        state_features=("straight_flush_hand_level", "rank_connectivity", "suit_density"),
    ),
    "five_kind": SemanticRequirement(
        mechanics=("five_kind_payoff",), state_features=("five_kind_hand_level", "rank_multiplicity")
    ),
    "flush_house": SemanticRequirement(
        mechanics=("flush_house_payoff",),
        state_features=("flush_house_hand_level", "rank_multiplicity", "suit_density"),
    ),
    "flush_five": SemanticRequirement(
        mechanics=("flush_five_payoff",),
        state_features=("flush_five_hand_level", "rank_multiplicity", "suit_density"),
    ),
    "hearts": SemanticRequirement(
        mechanics=("heart_payoff", "suit_conversion"), state_features=("heart_density",)
    ),
    "spades": SemanticRequirement(
        mechanics=("spade_payoff", "suit_conversion"), state_features=("spade_density",)
    ),
    "clubs": SemanticRequirement(
        mechanics=("club_payoff", "suit_conversion"), state_features=("club_density",)
    ),
    "diamonds": SemanticRequirement(
        mechanics=("diamond_payoff", "suit_conversion"), state_features=("diamond_density",)
    ),
    "low_ranks": SemanticRequirement(
        mechanics=("low_rank_payoff",), state_features=("low_rank_density",)
    ),
    "kings": SemanticRequirement(
        mechanics=("king_payoff", "held_rank_payoff"), state_features=("king_density",)
    ),
    "queens": SemanticRequirement(
        mechanics=("queen_payoff", "held_rank_payoff"), state_features=("queen_density",)
    ),
    "jacks": SemanticRequirement(
        mechanics=("jack_payoff",), state_features=("jack_density",)
    ),
    "tarot": SemanticRequirement(
        mechanics=("tarot_generation", "tarot_payoff"), state_features=("tarot_access",)
    ),
    "planet": SemanticRequirement(
        mechanics=("planet_generation", "planet_pack_targeting", "planet_payoff"),
        state_features=("hand_levels",),
    ),
    "discard": SemanticRequirement(
        mechanics=("discard_payoff", "discard_scaling"), state_features=("discard_capacity",)
    ),
    "blind_skip": SemanticRequirement(
        mechanics=("blind_skip_payoff",), state_features=("available_skip_tag", "ante", "blind_kind")
    ),
    "sell_value": SemanticRequirement(
        mechanics=("sell_value_payoff", "sell_value_scaling"), state_features=("joker_sell_values",)
    ),
    "joker_sacrifice": SemanticRequirement(
        mechanics=("joker_destruction_payoff", "joker_consumption"), state_features=("joker_slots",)
    ),
    "card_destruction": SemanticRequirement(
        mechanics=("card_destruction", "destruction_payoff"), state_features=("owned_deck_size",)
    ),
    "hand_repetition": SemanticRequirement(
        mechanics=("repeated_hand_payoff", "hand_switch_penalty"), state_features=("hand_play_history",)
    ),
    "enhanced_cards": SemanticRequirement(
        mechanics=("enhancement_payoff", "enhancement_generation"), state_features=("enhanced_card_density",)
    ),
    "no_face_cards": SemanticRequirement(
        mechanics=("no_face_payoff", "face_card_destruction"), state_features=("face_card_density",)
    ),
    "enhancement_consumption": SemanticRequirement(
        mechanics=("enhancement_consumption", "enhancement_feed_access"),
        state_features=("enhanced_card_density", "enhancements_consumed"),
    ),
}


# Kept as compatibility exports for diagnostics/tests that still distinguish the
# old broad channels.  They are derived from the explicit contract rather than
# acting as proof of coverage themselves.
BEHAVIOR_FEATURE_BONDS = frozenset({
    "aces", "cash", "clubs", "diamonds", "enhanced_cards", "flush", "flush_five",
    "flush_house", "four_kind", "glass", "gold_cards", "hearts", "held_cards",
    "held_retrigger", "high_card", "jacks", "kings", "low_ranks", "pair",
    "played_retrigger", "queens", "spades", "steel", "straight", "straight_flush",
    "three_kind", "two_pair", "five_kind", "full_house",
})
DEDICATED_SEMANTIC_BONDS = frozenset(set(BOND_IDS) - set(BEHAVIOR_FEATURE_BONDS))


@dataclass(frozen=True)
class SemanticCoverage:
    bond_id: str
    required_mechanics: tuple[str, ...]
    required_state_features: tuple[str, ...]
    explicit_sources: tuple[str, ...]

    @property
    def covered(self) -> bool:
        return bool(self.required_mechanics or self.required_state_features)


def explicit_role_sources_by_bond() -> dict[str, set[str]]:
    """Conservative diagnostics for existing role-enriched contribution sources."""
    mapping: dict[str, set[str]] = {bond_id: set() for bond_id in BOND_IDS}
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
                mapping[bond_id].add(source)
    return mapping


def audit_semantic_coverage() -> dict[str, SemanticCoverage]:
    role_sources = explicit_role_sources_by_bond()
    return {
        bond_id: SemanticCoverage(
            bond_id=bond_id,
            required_mechanics=BOND_SEMANTIC_REQUIREMENTS[bond_id].mechanics,
            required_state_features=BOND_SEMANTIC_REQUIREMENTS[bond_id].state_features,
            explicit_sources=tuple(sorted(role_sources.get(bond_id, ()))),
        )
        for bond_id in BOND_IDS
    }


def uncovered_bonds() -> tuple[str, ...]:
    catalogue = set(BOND_IDS)
    declared = set(BOND_SEMANTIC_REQUIREMENTS)
    missing = catalogue - declared
    unexplained = {
        bond_id
        for bond_id, requirement in BOND_SEMANTIC_REQUIREMENTS.items()
        if not requirement.explained
    }
    extra = declared - catalogue
    return tuple(sorted(missing | unexplained | extra))


def semantic_vocabulary() -> frozenset[str]:
    """All mechanic/state tokens required by the frozen strategic vocabulary."""
    tokens: set[str] = set()
    for requirement in BOND_SEMANTIC_REQUIREMENTS.values():
        tokens.update(requirement.mechanics)
        tokens.update(requirement.state_features)
    return frozenset(tokens)


def assert_catalogue_semantics_are_frozen() -> None:
    """Fail loudly if rank/evaluator catalogue and semantic contract diverge."""
    threshold_ids = set(canonical_rank_thresholds())
    catalogue_ids = set(BOND_IDS)
    requirement_ids = set(BOND_SEMANTIC_REQUIREMENTS)
    if threshold_ids != catalogue_ids or requirement_ids != catalogue_ids:
        raise AssertionError(
            "Bond semantic catalogue diverged: "
            f"ids={sorted(catalogue_ids)} thresholds={sorted(threshold_ids)} "
            f"requirements={sorted(requirement_ids)}"
        )
