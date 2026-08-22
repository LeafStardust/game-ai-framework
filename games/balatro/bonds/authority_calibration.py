from __future__ import annotations

"""Audit-pass-three rank authority calibration.

This module centralizes the final catalogue-audit corrections without spreading
threshold-only edits across every batch file. The evaluator modules still own
Bond identity and contributor calculation; this layer adjusts only rank geometry
and a few shared structural-density curves so R1-R5 authority is attainable and
meaningful.
"""

from games.balatro.bonds.model import BondRank


def _set(thresholds: dict[BondRank, float], r1: float, r2: float, r3: float, r4: float, r5: float) -> None:
    thresholds.clear()
    thresholds.update({
        BondRank.R1: float(r1),
        BondRank.R2: float(r2),
        BondRank.R3: float(r3),
        BondRank.R4: float(r4),
        BondRank.R5: float(r5),
    })


def _audited_hand_level_band(level: int) -> float:
    # Permanent hand investment must be capable of carrying real rank authority.
    # Extreme levels are intentionally required before level investment alone
    # begins approaching capstone strength.
    if level <= 1:
        return 0.0
    if level <= 3:
        return 1.0
    if level <= 6:
        return 3.0
    if level <= 10:
        return 5.0
    if level <= 15:
        return 8.0
    if level <= 24:
        return 12.0
    return 18.0


def _audited_suit_density(state, suit: str) -> float:
    from games.balatro.bonds import catalogue_batch_three as b3

    count = sum(
        1 for card in b3._deck(state)
        if str(getattr(card, "suit", "") or "").lower() == suit.lower()
        and str(getattr(card, "enhancement", "") or "").lower() != "stone"
    )
    return b3._band(count, ((13, 1.0), (17, 3.0), (21, 5.0), (26, 7.0), (32, 9.0), (40, 13.0), (46, 17.0), (50, 21.0)))


def _audited_rank_density(state, ranks: set[str]) -> float:
    from games.balatro.bonds import catalogue_batch_four as b4

    count = sum(1 for card in b4._deck(state) if str(getattr(card, "rank", "") or "").upper() in ranks)
    return b4._band(count, ((4, 1.0), (6, 3.0), (9, 5.0), (13, 7.0), (18, 9.0), (24, 13.0), (32, 17.0), (40, 21.0), (44, 23.0)))


def apply_rank_authority_audit() -> None:
    from games.balatro.bonds import catalogue_batch_one as b1
    from games.balatro.bonds import catalogue_batch_two as b2
    from games.balatro.bonds import catalogue_batch_three as b3
    from games.balatro.bonds import catalogue_batch_four as b4
    from games.balatro.bonds import catalogue_batch_five as b5
    from games.balatro.bonds import held_cards as hc

    # Shared permanent poker-hand progression. This fixes the implementation-pass
    # ceiling where even extreme permanent hand investment could not reach R4/R5.
    b1._level_band = _audited_hand_level_band
    b2._level_score = _audited_hand_level_band
    b3._level_score = _audited_hand_level_band

    # Structural density curves: ordinary density remains low authority, while
    # extreme suit/rank concentration can eventually become capstone commitment.
    original_suit_bond = b3._suit_bond

    def audited_suit_bond(state, bond_id, suit, specs):
        jokers = list(getattr(state, "jokers", ()) or ())
        parts = b3._joker_parts(jokers, specs)
        density = _audited_suit_density(state, suit)
        if density:
            parts.append(b3.BondContribution(f"{suit} density", density))
        return b3._finish(bond_id, parts, b3.SUIT_THRESHOLDS, target=suit.upper())

    b3._suit_bond = audited_suit_bond
    b4._rank_density = _audited_rank_density

    # Bonds whose implementation-pass maxima made R5 unreachable or made R4
    # impossible despite complete infrastructure. Thresholds are lowered only to
    # the strongest legitimate observed contribution envelope.
    _set(hc.HELD_CARDS_RANK_THRESHOLDS, 4, 8, 13, 18, 22)
    _set(b1.HELD_RETRIGGER_THRESHOLDS, 4, 8, 13, 17, 21)
    _set(b1.STEEL_THRESHOLDS, 4, 8, 13, 17, 20)
    _set(b1.ACES_THRESHOLDS, 4, 8, 13, 17, 20)
    _set(b1.NO_DISCARD_THRESHOLDS, 4, 8, 13, 18, 22)
    _set(b1.LUCKY_THRESHOLDS, 4, 8, 12, 15, 17)
    _set(b1.GLASS_THRESHOLDS, 4, 8, 12, 16, 19)

    _set(b2.STONE_THRESHOLDS, 4, 8, 13, 17, 20)
    _set(b2.GOLD_ECONOMY_THRESHOLDS, 4, 8, 13, 17, 21)
    _set(b2.DECK_THINNING_THRESHOLDS, 4, 7, 10, 13, 16)
    _set(b2.DECK_GROWTH_THRESHOLDS, 4, 7, 12, 18, 25)

    # Advanced hands with few direct Joker contributors still need a reachable
    # capstone when permanent hand investment is extreme.
    _set(b3.FULL_HOUSE_THRESHOLDS, 4, 8, 13, 19, 22)
    _set(b3.FLUSH_HOUSE_THRESHOLDS, 4, 8, 13, 19, 23)

    # Resource engine capstone: all major Tarot infrastructure together should
    # reach R5; one or two access pieces should remain R1/R2.
    _set(b4.TAROT_THRESHOLDS, 4, 9, 15, 22, 28)

    # Defining-payoff Bonds: the implementation-pass 30-point ceiling made R5
    # impossible even with every legitimate contributor and maximal state.
    _set(b5.BLIND_SKIP_THRESHOLDS, 4, 8, 12, 15, 18)
    _set(b5.SELL_VALUE_THRESHOLDS, 4, 9, 15, 20, 25)
    _set(b5.JOKER_SACRIFICE_THRESHOLDS, 4, 9, 14, 18, 23)
    _set(b5.CARD_DESTRUCTION_THRESHOLDS, 4, 9, 15, 20, 26)
    _set(b5.HAND_REPETITION_THRESHOLDS, 4, 8, 13, 16, 20)
    _set(b5.ENHANCED_CARDS_THRESHOLDS, 4, 8, 13, 16, 20)
