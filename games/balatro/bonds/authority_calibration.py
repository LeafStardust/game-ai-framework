from __future__ import annotations

"""Audit-pass-three rank authority calibration.

This module centralizes rank-geometry corrections without scattering threshold
edits across every evaluator file. Evaluator modules still own Bond identity and
contributor calculation; this layer calibrates only rank authority and a few
shared structural-density curves.
"""

from games.balatro.bonds.model import BondRank


def _table(r1: float, r2: float, r3: float, r4: float, r5: float) -> dict[BondRank, float]:
    return {
        BondRank.R1: float(r1),
        BondRank.R2: float(r2),
        BondRank.R3: float(r3),
        BondRank.R4: float(r4),
        BondRank.R5: float(r5),
    }


def _audited_hand_level_band(level: int) -> float:
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
        if str(getattr(card, "enhancement", "") or "").lower() != "stone"
        and (
            str(getattr(card, "suit", "") or "").lower() == suit.lower()
            or str(getattr(card, "enhancement", "") or "").lower() == "wild"
        )
    )
    return b3._band(
        count,
        ((13, 1.0), (17, 3.0), (21, 5.0), (26, 7.0), (32, 9.0), (40, 13.0), (46, 17.0), (50, 21.0)),
    )


def _audited_rank_density(state, ranks: set[str]) -> float:
    from games.balatro.bonds import catalogue_batch_four as b4

    # Stone cards retain a hidden underlying rank in the save, but mechanically
    # have no rank while Stone. Do not let that hidden rank establish Kings,
    # Queens, Jacks, or other rank-density authority.
    count = sum(
        1
        for card in b4._deck(state)
        if str(getattr(card, "enhancement", "") or "").lower() != "stone"
        and str(getattr(card, "rank", "") or "").upper() in ranks
    )
    return b4._band(
        count,
        ((4, 1.0), (6, 3.0), (9, 5.0), (13, 7.0), (18, 9.0), (24, 13.0), (32, 17.0), (40, 21.0), (44, 23.0)),
    )


def apply_rank_authority_audit() -> None:
    from games.balatro.bonds import catalogue_batch_one as b1
    from games.balatro.bonds import catalogue_batch_two as b2
    from games.balatro.bonds import catalogue_batch_three as b3
    from games.balatro.bonds import catalogue_batch_four as b4
    from games.balatro.bonds import catalogue_batch_five as b5
    from games.balatro.bonds import held_cards as hc

    b1._level_band = _audited_hand_level_band
    b2._level_score = _audited_hand_level_band
    b3._level_score = _audited_hand_level_band

    def audited_suit_bond(state, bond_id, suit, specs):
        jokers = list(getattr(state, "jokers", ()) or ())
        parts = b3._joker_parts(jokers, specs)
        density = _audited_suit_density(state, suit)
        if density:
            parts.append(b3.BondContribution(f"{suit} density", density))
        return b3._finish(bond_id, parts, b3.SUIT_THRESHOLDS, target=suit.upper())

    def audited_hand_bond(state, bond_id, hand, specs, thresholds):
        jokers = list(getattr(state, "jokers", ()) or ())
        parts = b3._joker_parts(jokers, specs)
        score = _audited_hand_level_band(b3._level(state, hand))
        if score:
            parts.append(b3.BondContribution(f"{hand} permanent hand level", score))
        return b3._finish(bond_id, parts, thresholds, target=hand)

    b3._suit_bond = audited_suit_bond
    b4._rank_density = _audited_rank_density

    hc.HELD_CARDS_RANK_THRESHOLDS = _table(4, 8, 13, 18, 22)
    b1.HELD_RETRIGGER_THRESHOLDS = _table(4, 8, 13, 17, 21)
    b1.STEEL_THRESHOLDS = _table(4, 8, 13, 17, 20)
    b1.ACES_THRESHOLDS = _table(4, 8, 13, 17, 20)
    b1.NO_DISCARD_THRESHOLDS = _table(4, 8, 13, 18, 22)
    b1.CASH_THRESHOLDS = _table(4, 9, 15, 22, 27)
    b1.LUCKY_THRESHOLDS = _table(4, 8, 12, 15, 17)
    b1.GLASS_THRESHOLDS = _table(4, 8, 12, 16, 19)

    b2.STONE_THRESHOLDS = _table(4, 8, 13, 17, 20)
    b2.GOLD_ECONOMY_THRESHOLDS = _table(4, 8, 13, 17, 21)
    b2.DECK_THINNING_THRESHOLDS = _table(4, 7, 10, 13, 16)
    b2.DECK_GROWTH_THRESHOLDS = _table(4, 7, 12, 18, 25)

    b3.FULL_HOUSE_THRESHOLDS = _table(4, 8, 13, 19, 22)
    b3.FLUSH_HOUSE_THRESHOLDS = _table(4, 8, 13, 19, 23)

    # The original advanced-hand evaluators delegate to _hand_bond(), which uses
    # shared HAND_THRESHOLDS.  Rebind these two evaluators so their audited,
    # bond-specific capstones are actually authoritative at runtime.
    def evaluate_full_house_bond(state):
        return audited_hand_bond(
            state,
            "full_house",
            "FULL_HOUSE",
            (("The Duo", 2.0, ("theduo",)), ("The Trio", 2.0, ("thetrio",))),
            b3.FULL_HOUSE_THRESHOLDS,
        )

    def evaluate_flush_house_bond(state):
        return audited_hand_bond(
            state,
            "flush_house",
            "FLUSH_HOUSE",
            (("Smeared Joker", 3.0, ("smearedjoker",)), ("The Duo", 1.0, ("theduo",)), ("The Trio", 1.0, ("thetrio",))),
            b3.FLUSH_HOUSE_THRESHOLDS,
        )

    b3.evaluate_full_house_bond = evaluate_full_house_bond
    b3.evaluate_flush_house_bond = evaluate_flush_house_bond
    b3.BATCH_THREE_EVALUATORS["full_house"] = evaluate_full_house_bond
    b3.BATCH_THREE_EVALUATORS["flush_house"] = evaluate_flush_house_bond

    # Five ordinary Joker slots can supply all five low-rank contributors (20)
    # and a heavily shaped 2-5 deck supplies the existing 7-point density cap.
    # R5=30 was therefore mathematically dead even at maximum commitment.
    b3.LOW_RANKS_THRESHOLDS = _table(4, 9, 15, 22, 27)

    b4.TAROT_THRESHOLDS = _table(4, 9, 15, 22, 28)

    # These capstones must be reachable on an ordinary five-slot board plus the
    # Bond's persistent state infrastructure; Negative/capacity RNG is not a
    # prerequisite for rank semantics.
    b5.DISCARD_THRESHOLDS = _table(4, 9, 15, 22, 26)
    b5.BLIND_SKIP_THRESHOLDS = _table(4, 8, 12, 15, 18)
    b5.SELL_VALUE_THRESHOLDS = _table(4, 9, 15, 20, 25)
    b5.JOKER_SACRIFICE_THRESHOLDS = _table(4, 9, 14, 18, 23)
    b5.CARD_DESTRUCTION_THRESHOLDS = _table(4, 9, 15, 20, 26)
    b5.HAND_REPETITION_THRESHOLDS = _table(4, 8, 13, 16, 20)
    b5.ENHANCED_CARDS_THRESHOLDS = _table(4, 8, 13, 16, 20)
