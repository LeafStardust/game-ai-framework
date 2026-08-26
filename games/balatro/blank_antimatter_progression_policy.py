from __future__ import annotations

"""Keep Blank Voucher admissible while it advances the Antimatter unlock.

Balatro unlocks Antimatter after ten Blank redemptions across the profile. Blank has
no current-run mechanical effect, so ordinary D3 persistent-value admission can
otherwise reject it before D14 has a chance to weigh progression against current-run
resources.

This adapter is deliberately admission-only. It does not force a purchase and does
not assign Blank a gameplay value. While Antimatter is observably locked, Blank may
enter D14 only when it is affordable and the existing D3 survival/reserve gate still
passes. D14 separately owns the bounded unlock-progression parent value.
"""

from dataclasses import replace

from games.balatro.actions import BUY_VOUCHER, BalatroAction
from games.balatro.shop_voucher_policy import BUY, HOLD, VoucherAcquisitionPolicy


def _label(candidate: object) -> str:
    return str(
        getattr(candidate, "label", None)
        or getattr(candidate, "name", None)
        or type(candidate).__name__
    )


def install_blank_antimatter_progression_policy() -> None:
    if getattr(VoucherAcquisitionPolicy, "_blank_antimatter_progression_installed", False):
        return

    original_decide = VoucherAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if _label(candidate) != "Blank" or decision.action != HOLD:
            return decision

        # Unknown profile state must not be interpreted as locked. This keeps the
        # autonomous path fail-closed outside live observations that expose the
        # public Antimatter center state.
        if not bool(getattr(state, "antimatter_unlock_observed", False)):
            return decision
        if bool(getattr(state, "antimatter_unlocked", False)):
            return decision

        price = int(getattr(decision, "price", 0) or 0)
        money_after = int(getattr(decision, "money_after", int(state.money) - price))
        minimum_money_after = max(
            int(getattr(self.thresholds, "minimum_money_after", 0) or 0),
            int(getattr(self.thresholds, "reserve_target", 0) or 0),
        )
        if money_after < minimum_money_after:
            return replace(
                decision,
                rationale=(
                    *tuple(decision.rationale),
                    "Blank progression withheld: current-run reserve remains authoritative over Antimatter unlock progress",
                    f"money after=${money_after}; required reserve=${minimum_money_after}",
                ),
            )

        profile = self.profiler.profile(state)
        allowed, survival_notes = self._early_survival_gate(
            state,
            profile,
            "Blank",
            price=price,
            money_after=money_after,
        )
        if not allowed:
            return replace(
                decision,
                rationale=(
                    *tuple(decision.rationale),
                    "Blank progression withheld by D3 survival readiness",
                    *tuple(survival_notes),
                ),
            )

        # D3's minimum persistent value is used only as an admission sentinel. The
        # D14 Blank authority replaces this number before any cross-family comparison.
        admission_value = max(
            float(getattr(decision, "persistent_value", 0.0) or 0.0),
            float(getattr(self.thresholds, "minimum_persistent_value", 0.0) or 0.0),
        )
        return replace(
            decision,
            action=BUY,
            executable_action=BalatroAction(BUY_VOUCHER, target=candidate),
            persistent_value=admission_value,
            rationale=(
                *tuple(decision.rationale),
                "D3 progression admission: Blank advances the still-locked Antimatter unlock",
                "Balatro requires ten Blank redemptions for Antimatter; this redemption is one real progression step",
                f"progression admission sentinel={admission_value:.3f}; not a D14 gameplay value",
                f"money after=${money_after}; survival/reserve gates passed",
                "D14 remains authoritative against Jokers, consumables, boosters, rerolls and END_SHOP",
            ),
        )

    VoucherAcquisitionPolicy.decide = decide
    VoucherAcquisitionPolicy._blank_antimatter_progression_installed = True
