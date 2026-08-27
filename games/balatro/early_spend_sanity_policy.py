from __future__ import annotations

"""Hard sanity gates for destructive early shop spending.

Long-horizon utility is useful only if the run survives long enough to realize it.
This layer therefore protects a small amount of early scoring capital from voucher
and unopened-booster purchases while the build is still fragile. It does not replace
D3/D8 valuation, predict hidden pack contents, or constrain established/mid-run
builds.
"""

from dataclasses import replace

from games.balatro.shop_booster_policy import BUY as BOOSTER_BUY
from games.balatro.shop_booster_policy import HOLD as BOOSTER_HOLD
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy


EARLY_ANTE_LIMIT = 2
EARLY_HARD_CASH_FLOOR = 5
EARLY_STRUCTURAL_CASH_FLOOR = 4

# Antimatter is the one Red/White voucher whose immediate Joker-slot creation is
# explicitly calibrated to compete against the weighted reserve cost all the way to
# $0. Other structural vouchers remain privileged, but they may not consume the last
# few dollars of a fragile Ante-1/2 run.
_FULL_WEIGHTED_RESERVE_EXCEPTION = {"Antimatter"}
_STRUCTURAL_LOW_FLOOR_EXCEPTIONS = {
    "Paint Brush",
    "Palette",
    "Grabber",
    "Nacho Tong",
}


def _scoring_ready(profile) -> bool:
    joker_count = len(tuple(getattr(profile, "joker_names", ()) or ()))
    invested_hand = max(
        (int(level) for _, level in tuple(getattr(profile, "hand_levels", ()) or ())),
        default=1,
    ) > 1
    return joker_count >= 3 or invested_hand


def _needs_early_cash_floor(profile) -> bool:
    return int(getattr(profile, "ante", 0) or 0) <= EARLY_ANTE_LIMIT and not _scoring_ready(profile)


def _cash_floor_safe(profile, money_after: int, *, floor: int = EARLY_HARD_CASH_FLOOR) -> bool:
    return not _needs_early_cash_floor(profile) or int(money_after) >= int(floor)


def _empty_joker_roster(profile) -> bool:
    return not tuple(getattr(profile, "joker_names", ()) or ())


def install_early_spend_sanity_policy() -> None:
    if getattr(VoucherAcquisitionPolicy, "_early_spend_sanity_installed", False):
        return

    original_voucher_gate = VoucherAcquisitionPolicy._early_survival_gate
    original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

    def voucher_gate(
        state,
        profile,
        label: str,
        *,
        price: int,
        money_after: int,
    ):
        allowed, notes = original_voucher_gate(
            state,
            profile,
            label,
            price=price,
            money_after=money_after,
        )
        if not allowed:
            return allowed, notes

        # Preserve the Red/White D3 contract: Antimatter's immediate extra Joker
        # slot is allowed to compete under the ordinary weighted-reserve model rather
        # than a second hard cash veto.
        if label in _FULL_WEIGHTED_RESERVE_EXCEPTION:
            return True, (
                *notes,
                "D3 Antimatter keeps weighted-reserve authority; no additional hard cash floor",
            )

        floor = (
            EARLY_STRUCTURAL_CASH_FLOOR
            if label in _STRUCTURAL_LOW_FLOOR_EXCEPTIONS
            else EARLY_HARD_CASH_FLOOR
        )
        if _cash_floor_safe(profile, money_after, floor=floor):
            return True, notes
        return False, (
            *notes,
            "D3 hard early cash-floor hold: permanent utility cannot spend through immediate survival capital",
            f"D3 money after=${int(money_after)} hard early floor=${floor}",
        )

    def booster_recommend(self, state, action):
        recommendation = original_booster_recommend(self, state, action)
        if getattr(recommendation, "decision", None) != BOOSTER_BUY:
            return recommendation

        try:
            price = int(self._price(action.target))
            money_after = int(state.money) - price
            profile = self.build_profiler.profile(state)
        except (AttributeError, TypeError, ValueError):
            return recommendation

        if _cash_floor_safe(profile, money_after):
            return recommendation

        # A Buffoon BUY reaching this layer has already passed D8's public eligible-
        # Joker expectation *after* the ordinary price/interest/reserve cost was
        # charged. On an empty early roster that is immediate scoring-engine access,
        # not optional side development. Do not let a second blanket cash floor erase
        # that mechanically positive D8 admission; D14 must be allowed to compare it
        # against the other admitted shop families normally.
        if (
            str(getattr(recommendation, "family", "") or "").upper() == "BUFFOON"
            and _empty_joker_roster(profile)
        ):
            return replace(
                recommendation,
                rationale=(
                    *tuple(getattr(recommendation, "rationale", ()) or ()),
                    "D8 early empty-roster Buffoon exception: underlying public-Joker EV already beat weighted reserve economics",
                    "hard cash floor does not suppress first-engine access; canonical D14 remains final shop authority",
                ),
            )

        return replace(
            recommendation,
            decision=BOOSTER_HOLD,
            rationale=(
                *tuple(getattr(recommendation, "rationale", ()) or ()),
                "D8 hard early cash-floor hold: unopened-pack EV cannot spend through immediate survival capital",
                f"D8 money after=${money_after} hard early floor=${EARLY_HARD_CASH_FLOOR}",
            ),
        )

    VoucherAcquisitionPolicy._early_survival_gate = staticmethod(voucher_gate)
    BuildAwareShopBoosterPolicy.recommend = booster_recommend
    VoucherAcquisitionPolicy._early_spend_sanity_installed = True
    BuildAwareShopBoosterPolicy._early_spend_sanity_installed = True
