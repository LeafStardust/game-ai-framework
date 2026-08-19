from __future__ import annotations

"""Conservative policy corrections derived from the 2026-08-19 three-run review.

The reviewed Red/White attempts exposed repeated development spending while the
Joker board was still incomplete, plus late speculative pack/voucher spending that
was not improving the run's actual scoring engine.  These guards intentionally sit
above the existing D3/D8 models: they do not invent hidden outcomes or replace the
strategy tree; they only reject clearly premature or low-leverage spending.
"""

from dataclasses import replace

from games.balatro.shop_booster_policy import HOLD as BOOSTER_HOLD
from games.balatro.shop_voucher_policy import HOLD as VOUCHER_HOLD, VoucherAcquisitionPolicy
from games.balatro.strategy import COMMITTED, MATURE
from games.balatro.strategy_booster_policy import StrategyAwareShopBoosterPolicy


_SPECULATIVE_PACKS = frozenset({"STANDARD", "ARCANA", "SPECTRAL", "CELESTIAL"})
_PLANET_MARKET_VOUCHERS = frozenset({"Planet Merchant", "Planet Tycoon"})


def _ante(state) -> int:
    return max(1, int(getattr(state, "ante", 1) or 1))


def _free_joker_slots(state) -> int:
    slots = max(0, int(getattr(state, "joker_slots", 5) or 5))
    owned = len(getattr(state, "jokers", ()) or ())
    return max(0, slots - owned)


def _has_hand_specialization(state) -> bool:
    """Public evidence that Planet frequency has a concrete refinement target."""
    hands = getattr(state, "hands", {}) or {}
    values = hands.values() if hasattr(hands, "values") else ()
    for hand in values:
        level = getattr(hand, "level", None)
        if level is None and isinstance(hand, dict):
            level = hand.get("level")
        try:
            if int(level or 1) > 1:
                return True
        except (TypeError, ValueError):
            continue
    return False


def install_three_run_review_policy() -> None:
    if getattr(StrategyAwareShopBoosterPolicy, "_three_run_review_installed", False):
        return

    original_booster_recommend = StrategyAwareShopBoosterPolicy.recommend

    def booster_recommend(self, state, action):
        recommendation = original_booster_recommend(self, state, action)
        family = str(getattr(recommendation, "family", "")).upper()
        if family not in _SPECULATIVE_PACKS:
            return recommendation

        ante = _ante(state)
        free_slots = _free_joker_slots(state)

        # The failed runs repeatedly spent on deck/consumable development while the
        # scoring board still had large empty Joker capacity.  Buffoon packs remain
        # exempt because they directly address that deficit.
        if ante >= 2 and free_slots >= 2:
            return replace(
                recommendation,
                decision=BOOSTER_HOLD,
                rationale=(
                    *recommendation.rationale,
                    f"three-run review guard: {free_slots} Joker slots remain open at Ante {ante}",
                    "prioritize direct/Buffoon Joker development before speculative Standard/Arcana/Spectral/Celestial spending",
                ),
            )

        # Once a route is committed, late speculative packs must clear a meaningful
        # advantage rather than repeatedly winning by tiny positive EV margins.
        resolution = self.strategy_tracker.observe(state)
        if ante >= 5 and resolution.active_status in {COMMITTED, MATURE}:
            late_floor = 1.50
            advantage = float(getattr(recommendation, "advantage_over_save", float("-inf")))
            if advantage < late_floor:
                return replace(
                    recommendation,
                    decision=BOOSTER_HOLD,
                    rationale=(
                        *recommendation.rationale,
                        f"three-run review late-pack floor={late_floor:.2f}; observed advantage={advantage:.3f}",
                        "committed late build preserves cash unless speculative pack value is clearly material",
                    ),
                )

        return recommendation

    StrategyAwareShopBoosterPolicy.recommend = booster_recommend
    StrategyAwareShopBoosterPolicy._three_run_review_installed = True

    original_voucher_decide = VoucherAcquisitionPolicy.decide

    def voucher_decide(self, state, candidate):
        decision = original_voucher_decide(self, state, candidate)
        label = str(
            getattr(candidate, "label", getattr(candidate, "name", type(candidate).__name__))
        )
        if (
            decision.action != VOUCHER_HOLD
            and label in _PLANET_MARKET_VOUCHERS
            and _ante(state) >= 4
            and not _has_hand_specialization(state)
        ):
            return replace(
                decision,
                action=VOUCHER_HOLD,
                executable_action=None,
                rationale=(
                    *decision.rationale,
                    "three-run review guard: Planet-market voucher blocked without a leveled poker-hand specialization",
                    "increasing Planet shop frequency is refinement spending and needs an actual hand-level target",
                ),
            )
        return decision

    VoucherAcquisitionPolicy.decide = voucher_decide
    VoucherAcquisitionPolicy._three_run_review_installed = True
