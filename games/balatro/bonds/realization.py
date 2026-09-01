from __future__ import annotations

from typing import Any, Callable

from games.balatro.bonds.model import BondDevelopment
from games.balatro.bonds.realization_held import HELD_REALIZERS
from games.balatro.bonds.realization_common import COMMON_REALIZERS
from games.balatro.bonds.realization_rank_state import RANK_STATE_REALIZERS
from games.balatro.bonds.realization_engine import ENGINE_REALIZERS
from games.balatro.bonds.realization_advanced import ADVANCED_REALIZERS
from games.balatro.bonds.realization_engine_order_audit import ENGINE_AUDIT_REALIZERS
from games.balatro.bonds.realization_engine_triggered import TRIGGERED_ENGINE_OVERRIDES
from games.balatro.bonds.realization_engine_liveness_audit import ENGINE_LIVENESS_AUDIT_REALIZERS
from games.balatro.bonds.realization_contract_compat import CONTRACT_COMPAT_REALIZERS

Realizer = Callable[[BondDevelopment, Any], BondDevelopment]

REALIZERS: dict[str, Realizer] = {}
for family in (HELD_REALIZERS, COMMON_REALIZERS, RANK_STATE_REALIZERS, ENGINE_REALIZERS, ADVANCED_REALIZERS):
    overlap = set(REALIZERS).intersection(family)
    if overlap:
        raise RuntimeError(f"Duplicate Bond realizer registration: {sorted(overlap)}")
    REALIZERS.update(family)

# Mechanical audit layers refine specific families. Contract compatibility runs
# last so explicit action-window telemetry remains strict while ordinary public
# state may still realize a mechanically available engine/opportunity.
REALIZERS.update(ENGINE_AUDIT_REALIZERS)
REALIZERS.update(TRIGGERED_ENGINE_OVERRIDES)
REALIZERS.update(ENGINE_LIVENESS_AUDIT_REALIZERS)
REALIZERS.update(CONTRACT_COMPAT_REALIZERS)

# Temporary migration bridges. These remap legacy realizer implementation keys to
# the frozen strategic vocabulary without changing legitimate Burnt/Vampire Joker
# mechanic checks inside those realizers. Delete these bridges once the family
# modules themselves use only canonical Bond IDs.
for legacy_id, canonical_id in (
    ("burnt", "hand_leveling"),
    ("gold_economy", "gold_cards"),
    ("vampire", "enhancement_consumption"),
):
    legacy = REALIZERS.pop(legacy_id, None)
    if legacy is not None:
        REALIZERS[canonical_id] = legacy

FROZEN_BOND_IDS = (
    "hand_leveling", "held_cards", "held_retrigger", "steel", "pair", "high_card", "aces",
    "no_discard", "cash", "lucky", "glass", "face_cards", "two_pair", "three_kind",
    "four_kind", "straight", "flush", "played_retrigger", "stone", "gold_cards",
    "deck_thinning", "deck_growth", "full_house", "straight_flush", "five_kind",
    "flush_house", "flush_five", "hearts", "spades", "clubs", "diamonds", "low_ranks",
    "kings", "queens", "jacks", "tarot", "planet", "discard", "blind_skip", "sell_value",
    "joker_sacrifice", "card_destruction", "hand_repetition", "enhanced_cards", "no_face_cards",
    "enhancement_consumption",
)


def missing_realizers() -> tuple[str, ...]:
    return tuple(sorted(set(FROZEN_BOND_IDS) - set(REALIZERS)))


def extra_realizers() -> tuple[str, ...]:
    return tuple(sorted(set(REALIZERS) - set(FROZEN_BOND_IDS)))


def realize_bond(dev: BondDevelopment, state: Any) -> BondDevelopment:
    try:
        fn = REALIZERS[dev.bond_id]
    except KeyError as exc:
        raise KeyError(f"No Realizer registered for Bond {dev.bond_id!r}") from exc
    result = fn(dev, state)
    if result.rank != dev.rank:
        raise AssertionError(f"Realizer mutated rank for {dev.bond_id}: {dev.rank} -> {result.rank}")
    if result.contribution != dev.contribution:
        raise AssertionError(
            f"Realizer mutated contribution for {dev.bond_id}: {dev.contribution} -> {result.contribution}"
        )
    return result
