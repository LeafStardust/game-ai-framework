from __future__ import annotations

"""Stable live decision-quality guards derived from production validation.

These are authority corrections, not tuning knobs:
- zero-cost autonomous-safe boosters are opened when ordinary/default D8 semantics
  would otherwise reject them only for value/probability reasons;
- off-build exotic Planets cannot bootstrap relevance from a stray level increase;
- pack Planet relevance uses direct public hand-development evidence only.

Joker replacement admission is intentionally not overridden here. D2 owns the
literal build transition and transaction economics for BUY/REPLACE/HOLD.
"""

from dataclasses import replace

from games.balatro.actions import BUY_BOOSTER
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS
from games.balatro.shop_booster_policy import (
    BUY,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
)
import games.balatro.planet_relevance_policy as planet_relevance


# These hands are rare enough that a Planet level by itself must not create its own
# justification. This is the Neptune failure observed live: Straight Flush reached
# level 2/3 while its play count remained exactly zero.
_EXOTIC_HANDS = frozenset(
    {
        "STRAIGHT_FLUSH",
        "FIVE_OF_A_KIND",
        "FLUSH_HOUSE",
        "FLUSH_FIVE",
    }
)


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _hand_key(value: object) -> str:
    return "_".join(str(value or "").strip().upper().replace("-", " ").replace("_", " ").split())


def _strict_planet_hand_relevant(state, candidate):
    """Require direct public evidence before an exotic Planet becomes relevant.

    Canonical StrategyDelta already prices the exact persistent hand-level change.
    This guard exists only to stop an exotic hand level from manufacturing its own
    future justification when the run has never demonstrated that hand. Historical
    StrategyPlan/pinned-strategy escape hatches are intentionally excluded.
    """
    hand_type = _hand_key(getattr(candidate, "hand_type", ""))
    if not hand_type:
        return False, ("Planet target hand is unavailable",)

    plays = getattr(state, "hand_play_counts", {}) or {}
    played = int(plays.get(hand_type, 0) or 0)
    total = sum(max(0, int(value or 0)) for value in plays.values())
    concentration = played / total if total > 0 else 0.0
    level = int((getattr(state, "hand_levels", {}) or {}).get(hand_type, 1) or 1)

    # Preserve canonical B4/D9 behavior for ordinary developed hands. A levelled Pair,
    # Straight, Flush, etc. is legitimate public build-path evidence even when a
    # synthetic test state has no play-count telemetry.
    if hand_type not in _EXOTIC_HANDS and level > 1:
        return True, (f"Planet target {hand_type} is already developed to level {level}",)

    if played >= 3 and concentration >= 0.20:
        return True, (
            f"Planet target {hand_type} has sustained use: plays={played}, concentration={concentration:.3f}",
        )
    if level >= 3 and played >= 2 and concentration >= 0.15:
        return True, (
            f"Planet target {hand_type} has sustained developed use: level={level}, plays={played}, concentration={concentration:.3f}",
        )

    if played == 0:
        return False, (
            f"Planet target {hand_type} has zero play history; level={level} is insufficient public evidence",
            f"Planet target {hand_type} has weak public history: level={level}, plays=0, concentration=0.000",
        )
    return False, (
        f"Planet target {hand_type} has weak public history: level={level}, plays={played}, concentration={concentration:.3f}",
    )


def _planet_candidate_from_label(label: str):
    target = _token(label)
    for planet in PLANET_CARDS.values():
        if _token(planet.name) == target:
            return planet
    return None


def _default_d8_thresholds(policy: BuildAwareShopBoosterPolicy) -> bool:
    """Return whether D8 is using the canonical default admission thresholds."""
    return policy.thresholds == BoosterAcquisitionThresholds()


def _free_booster_safe_to_open(state, result) -> bool:
    """Open only families whose post-open path is already autonomous-safe.

    D9/D10 now cover visible Standard, Celestial, Arcana, and Spectral choices and
    their deterministic targets. Buffoon still requires capacity because PACK_SELECT
    cannot autonomously sell an incumbent first.
    """
    family = str(getattr(result, "family", "") or "").upper()
    if family in {"STANDARD", "CELESTIAL", "ARCANA", "SPECTRAL"}:
        return True
    if family == "BUFFOON":
        jokers = tuple(getattr(state, "jokers", ()) or ())
        slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        return len(jokers) < slots
    return False


def install_live_decision_quality_policy() -> None:
    # Zero-cost autonomous-safe packs have no resource downside, but this authority
    # must not bypass custom playbook D8 thresholds.
    if not getattr(BuildAwareShopBoosterPolicy, "_free_booster_authority_installed", False):
        original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

        def recommend(self, state, action):
            result = original_booster_recommend(self, state, action)
            if action.name != BUY_BOOSTER:
                return result
            try:
                price = int(self._price(action.target))
            except (AttributeError, TypeError, ValueError):
                return result
            if (
                price != 0
                or result.family is None
                or not _default_d8_thresholds(self)
                or not _free_booster_safe_to_open(state, result)
            ):
                return result
            return replace(
                result,
                decision=BUY,
                total=max(float(result.total), float(self.parent_hold_baseline) + max(0.50, float(result.option_utility))),
                advantage_over_save=max(float(result.advantage_over_save), 0.50, float(result.option_utility)),
                price_penalty=0.0,
                interest_penalty=0.0,
                reserve_penalty=0.0,
                rationale=(
                    *result.rationale,
                    "FREE BOOSTER AUTHORITY: $0 autonomous-safe pack is opened; post-open Skip remains available",
                ),
            )

        BuildAwareShopBoosterPolicy.recommend = recommend
        BuildAwareShopBoosterPolicy._free_booster_authority_installed = True

    # Preserve the direct public-evidence exotic-hand guard. The historical D4
    # relevance wrapper is inert; this assignment remains compatibility-only for
    # callers that still import its helper symbol during migration cleanup.
    planet_relevance._planet_hand_relevant = _strict_planet_hand_relevant

    if not getattr(BalatroPackPolicy, "_strict_planet_relevance_installed", False):
        original_pack_score = BalatroPackPolicy.score_action

        def score_action(self, state, action):
            scored = original_pack_score(self, state, action)
            choice = getattr(scored.action, "target", None)
            if str(getattr(choice, "kind", "") or "").upper() != "PLANET":
                return scored
            candidate = _planet_candidate_from_label(str(getattr(choice, "label", "") or ""))
            if candidate is None:
                return scored
            relevant, notes = _strict_planet_hand_relevant(state, candidate)
            if relevant:
                return PackActionScore(scored.action, scored.total, (*scored.notes, *notes))
            return PackActionScore(
                scored.action,
                min(-1.0, float(getattr(self, "skip_bias", 0.35)) - 1.0),
                (*scored.notes, *notes, "exotic Planet public-evidence veto applies inside booster packs too"),
            )

        BalatroPackPolicy.score_action = score_action
        BalatroPackPolicy._strict_planet_relevance_installed = True
