from __future__ import annotations

"""Canonical Bond vocabulary for the Currency-Wars-style strategic layer.

Bond IDs describe run-level strategic axes. Joker/component names belong in
mechanical descriptors and contribution sources, not in this vocabulary.
"""

BOND_IDS: tuple[str, ...] = (
    "hand_leveling",
    "held_cards",
    "held_retrigger",
    "steel",
    "pair",
    "high_card",
    "aces",
    "no_discard",
    "cash",
    "lucky",
    "glass",
    "face_cards",
    "two_pair",
    "three_kind",
    "four_kind",
    "straight",
    "flush",
    "played_retrigger",
    "stone",
    "gold_cards",
    "deck_thinning",
    "deck_growth",
    "full_house",
    "straight_flush",
    "five_kind",
    "flush_house",
    "flush_five",
    "hearts",
    "spades",
    "clubs",
    "diamonds",
    "low_ranks",
    "kings",
    "queens",
    "jacks",
    "tarot",
    "planet",
    "discard",
    "blind_skip",
    "sell_value",
    "joker_sacrifice",
    "card_destruction",
    "hand_repetition",
    "enhanced_cards",
    "no_face_cards",
    "enhancement_consumption",
)

BOND_ID_SET = frozenset(BOND_IDS)

# Migration-only aliases. New code must emit canonical IDs directly. These exist
# solely to identify old persisted/test vocabulary while consumers are migrated;
# remove them at the cleanup gate once no legacy references remain.
LEGACY_BOND_ID_ALIASES: dict[str, str] = {
    "burnt": "hand_leveling",
    "gold_economy": "gold_cards",
    "vampire": "enhancement_consumption",
}


def canonical_bond_id(bond_id: str) -> str:
    return LEGACY_BOND_ID_ALIASES.get(str(bond_id), str(bond_id))
