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


def _scoring_ready(profile) -> bool:
    joker_count = len(tuple(getattr(profile, "joker_names", ()) or ()))
    invested_hand = max(
        (int(level) for _, level in tuple(getattr(profile, "hand_levels", ()) or ())),
        default=1,
    ) > 1
    return joker_count >= 3 or invested_hand


def _needs_early_cash_floor(profile) -> bool:
    return int(getattr(profile, "ante", 0) or 0) <= EARLY_ANTE_LIMIT and not _scoring_ready(profile)


def _cash_floor_safe(profile, money_after: int) -> bool:
    return not _needs_early_cash_floor(profile) or int(money_after) >= EARLY_HARD_CASH_FLOOR


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
        if _cash_floor_safe(profile, money_after):
            return True, notes
        return False, (
            *notes,
            "D3 hard early cash-floor hold: permanent utility cannot spend through immediate survival capital",
            f"D3 money after=${int(money_after)} hard early floor=${EARLY_HARD_CASH_FLOOR}",
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
