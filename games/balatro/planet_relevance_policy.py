from __future__ import annotations

"""Prevent D4 from buying Planets for strategically irrelevant hands.

Generic B4 assigns intrinsic value to HAND_LEVEL, which is correct structurally but
can make an arbitrary Planet look useful even when its hand has never been played
and no canonical Bond currently targets it. This guard preserves Planet purchases
for demonstrated/developed/Bond-relevant hands and fails closed for speculative
level-1 zero-history hands such as pointless Neptune purchases.
"""

from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_all_bonds
from games.balatro.bonds.model import BondRank
from games.balatro.planet_scaler_authority import has_planet_use_scaler
from games.balatro.shop_consumable_policy import HOLD, ConsumableAcquisitionPolicy


def _normalize(value: object) -> str:
    return "".join(ch for ch in str(value).upper() if ch.isalnum())


def _planet_hand_relevant(state, candidate) -> tuple[bool, tuple[str, ...]]:
    hand_type = str(getattr(candidate, "hand_type", "") or "").upper()
    if not hand_type:
        return False, ("Planet target hand is unavailable",)

    played = int((getattr(state, "hand_play_counts", {}) or {}).get(hand_type, 0) or 0)
    level = int((getattr(state, "hand_levels", {}) or {}).get(hand_type, 1) or 1)
    if played > 0:
        return True, (f"Planet target {hand_type} has been played {played} time(s)",)
    if level > 1:
        return True, (f"Planet target {hand_type} is already developed to level {level}",)

    normalized_hand = _normalize(hand_type)
    try:
        developments = evaluate_all_bonds(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        developments = ()
    for development in developments:
        if development.rank < BondRank.R1:
            continue
        target = _normalize(development.target or "")
        if target and target == normalized_hand:
            return True, (
                f"Planet target {hand_type} is supported by {development.bond_id} {development.rank.name}",
            )

    return False, (
        f"Planet target {hand_type} has zero play history, level 1, and no R1+ Bond target",
    )


def install_planet_relevance_policy() -> None:
    if getattr(ConsumableAcquisitionPolicy, "_planet_relevance_installed", False):
        return

    original_decide = ConsumableAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if str(getattr(candidate, "category", "")).upper() != "PLANET":
            return decision
        if decision.action == HOLD:
            return decision
        # D4 has already applied the cash-reserve guard before admitting this
        # BUY_AND_USE. An active Planet-use scaler makes even an off-path Planet
        # permanent engine growth, so ordinary hand relevance must not veto it.
        if has_planet_use_scaler(state):
            return decision

        relevant, rationale = _planet_hand_relevant(state, candidate)
        if relevant:
            return replace(decision, rationale=(*decision.rationale, *rationale))

        return replace(
            decision,
            action=HOLD,
            selected=None,
            rationale=(
                *decision.rationale,
                *rationale,
                "D4 Planet relevance veto: generic HAND_LEVEL value cannot justify speculative off-build leveling",
            ),
        )

    ConsumableAcquisitionPolicy.decide = decide
    ConsumableAcquisitionPolicy._planet_relevance_installed = True
