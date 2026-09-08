from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from games.balatro.bonds.model import BondRank


RANK_ORDER = (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5)


@dataclass(frozen=True)
class RankProgressionAudit:
    bond_id: str
    thresholds: tuple[float, float, float, float, float]
    normalized: tuple[float, float, float, float, float]
    gaps: tuple[float, float, float, float]
    issues: tuple[str, ...]

    @property
    def healthy(self) -> bool:
        return not self.issues


def audit_rank_progression(
    bond_id: str,
    thresholds: Mapping[BondRank, float],
) -> RankProgressionAudit:
    """Validate one Bond's R1-R5 geometry against semantic progression bands.

    The rank ladder is intended to mean:
      R1 recognition / credible direction
      R2 supported direction
      R3 established build axis
      R4 major power engine
      R5 capstone commitment

    This audit is deliberately scale-free. Bonds may use different absolute
    contribution economies, but their five thresholds must still occupy distinct
    portions of that Bond's own R5 scale rather than bunching into one region.
    """
    missing = [rank for rank in RANK_ORDER if rank not in thresholds]
    if missing:
        return RankProgressionAudit(
            bond_id=bond_id,
            thresholds=tuple(),
            normalized=tuple(),
            gaps=tuple(),
            issues=(f"missing thresholds: {','.join(rank.name for rank in missing)}",),
        )

    values = tuple(float(thresholds[rank]) for rank in RANK_ORDER)
    issues: list[str] = []

    if any(value <= 0.0 for value in values):
        issues.append("thresholds must be positive")
    if any(b <= a for a, b in zip(values, values[1:])):
        issues.append("thresholds must be strictly increasing")

    r5 = values[-1]
    if r5 <= 0.0:
        normalized = (0.0,) * 5
    else:
        normalized = tuple(value / r5 for value in values)

    bands = (
        (0.10, 0.40, "R1 recognition"),
        (0.20, 0.62, "R2 support"),
        (0.40, 0.78, "R3 establishment"),
        (0.60, 0.92, "R4 power"),
        (1.00, 1.00, "R5 capstone"),
    )
    for ratio, (lo, hi, label) in zip(normalized, bands):
        if ratio < lo - 1e-9 or ratio > hi + 1e-9:
            issues.append(f"{label} ratio {ratio:.3f} outside [{lo:.2f}, {hi:.2f}]")

    gaps = tuple(b - a for a, b in zip(values, values[1:]))
    if r5 > 0.0:
        normalized_gaps = tuple(gap / r5 for gap in gaps)
        for index, ratio in enumerate(normalized_gaps, start=1):
            if ratio < 0.075 - 1e-9:
                issues.append(f"R{index}->R{index + 1} gap too compressed ({ratio:.3f} of R5)")

    return RankProgressionAudit(
        bond_id=bond_id,
        thresholds=values,
        normalized=normalized,
        gaps=gaps,
        issues=tuple(issues),
    )


def canonical_rank_thresholds() -> dict[str, Mapping[BondRank, float]]:
    """Return the post-audit threshold table used by each canonical Bond."""
    from games.balatro.bonds import catalogue_batch_one as b1
    from games.balatro.bonds import catalogue_batch_two as b2
    from games.balatro.bonds import catalogue_batch_three as b3
    from games.balatro.bonds import catalogue_batch_four as b4
    from games.balatro.bonds import catalogue_batch_five as b5
    from games.balatro.bonds.burnt import BURNT_RANK_THRESHOLDS
    from games.balatro.bonds.gold_cards import GOLD_CARDS_THRESHOLDS
    from games.balatro.bonds.held_cards import HELD_CARDS_RANK_THRESHOLDS
    from games.balatro.bonds.mechanical_residue import SUIT_THRESHOLDS
    from games.balatro.bonds.no_face_cards import NO_FACE_CARDS_RANK_THRESHOLDS
    from games.balatro.bonds.vampire import VAMPIRE_THRESHOLDS

    return {
        "hand_leveling": BURNT_RANK_THRESHOLDS,
        "held_cards": HELD_CARDS_RANK_THRESHOLDS,
        "held_retrigger": b1.HELD_RETRIGGER_THRESHOLDS,
        "steel": b1.STEEL_THRESHOLDS,
        "pair": b1.PAIR_THRESHOLDS,
        "high_card": b1.HIGH_CARD_THRESHOLDS,
        "aces": b1.ACES_THRESHOLDS,
        "no_discard": b1.NO_DISCARD_THRESHOLDS,
        "cash": b1.CASH_THRESHOLDS,
        "lucky": b1.LUCKY_THRESHOLDS,
        "glass": b1.GLASS_THRESHOLDS,
        "face_cards": b1.FACE_CARDS_THRESHOLDS,
        "two_pair": b2.TWO_PAIR_THRESHOLDS,
        "three_kind": b2.THREE_KIND_THRESHOLDS,
        "four_kind": b2.FOUR_KIND_THRESHOLDS,
        "straight": b2.STRAIGHT_THRESHOLDS,
        "flush": b2.FLUSH_THRESHOLDS,
        "played_retrigger": b2.PLAYED_RETRIGGER_THRESHOLDS,
        "stone": b2.STONE_THRESHOLDS,
        "gold_cards": GOLD_CARDS_THRESHOLDS,
        "deck_thinning": b2.DECK_THINNING_THRESHOLDS,
        "deck_growth": b2.DECK_GROWTH_THRESHOLDS,
        "full_house": b3.FULL_HOUSE_THRESHOLDS,
        "straight_flush": b3.STRAIGHT_FLUSH_THRESHOLDS,
        "five_kind": b3.FIVE_KIND_THRESHOLDS,
        "flush_house": b3.FLUSH_HOUSE_THRESHOLDS,
        "flush_five": b3.FLUSH_FIVE_THRESHOLDS,
        "hearts": SUIT_THRESHOLDS,
        "spades": SUIT_THRESHOLDS,
        "clubs": SUIT_THRESHOLDS,
        "diamonds": SUIT_THRESHOLDS,
        "low_ranks": b3.LOW_RANKS_THRESHOLDS,
        "kings": b4.KINGS_THRESHOLDS,
        "queens": b4.QUEENS_THRESHOLDS,
        "jacks": b4.JACKS_THRESHOLDS,
        "tarot": b4.TAROT_THRESHOLDS,
        "planet": b4.PLANET_THRESHOLDS,
        "discard": b5.DISCARD_THRESHOLDS,
        "blind_skip": b5.BLIND_SKIP_THRESHOLDS,
        "sell_value": b5.SELL_VALUE_THRESHOLDS,
        "joker_sacrifice": b5.JOKER_SACRIFICE_THRESHOLDS,
        "card_destruction": b5.CARD_DESTRUCTION_THRESHOLDS,
        "hand_repetition": b5.HAND_REPETITION_THRESHOLDS,
        "enhanced_cards": b5.ENHANCED_CARDS_THRESHOLDS,
        "no_face_cards": NO_FACE_CARDS_RANK_THRESHOLDS,
        "enhancement_consumption": VAMPIRE_THRESHOLDS,
    }


def audit_all_rank_progressions() -> dict[str, RankProgressionAudit]:
    return {
        bond_id: audit_rank_progression(bond_id, thresholds)
        for bond_id, thresholds in canonical_rank_thresholds().items()
    }
