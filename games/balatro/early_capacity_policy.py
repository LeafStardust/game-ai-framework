from __future__ import annotations

"""Early-run persistent capacity priority.

Antes 1-2 are survival/flexibility stages. Permanent hand-size capacity has a long
remaining horizon and improves future hand construction regardless of which scoring
route eventually wins. This patch only resolves the narrow conflict between an
admitted Paint Brush and a currently-selected Celestial/Planet booster; it does not
override scoring Jokers, emergency economy, or other voucher decisions.
"""

from dataclasses import replace

from games.balatro.actions import BUY_BOOSTER, BUY_VOUCHER
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_voucher_policy import BUY, VoucherAcquisitionPolicy


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _label(item: object) -> str:
    if isinstance(item, str):
        return item
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or type(item).__name__
    )


def _is_paint_brush(action) -> bool:
    return (
        getattr(action, "name", None) == BUY_VOUCHER
        and _normalize(_label(getattr(action, "target", None))) == "paintbrush"
    )


def _is_celestial_booster(action) -> bool:
    if getattr(action, "name", None) != BUY_BOOSTER:
        return False
    token = _normalize(_label(getattr(action, "target", None)))
    return "celestial" in token or "planet" in token


def install_early_capacity_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_early_capacity_policy_installed", False):
        return

    original_decide = BuildAwareShopArbiter.decide

    def decide(self, state, visible_actions, *, reroll_cost: int | None):
        result = original_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante > 2 or not _is_celestial_booster(result.action):
            return result

        paint_action = next(
            (action for action in visible_actions if _is_paint_brush(action)),
            None,
        )
        if paint_action is None:
            return result

        item_estimator = getattr(self.shop_policy, "item_value_estimator", None)
        resource_valuator = getattr(self.shop_policy, "resource_valuator", None)
        voucher_policy = VoucherAcquisitionPolicy(
            item_value_estimator=item_estimator,
            resource_valuator=resource_valuator,
        )
        voucher = voucher_policy.decide(state, paint_action.target)
        if voucher.action != BUY or voucher.executable_action is None:
            return result

        # Paint Brush is bought first, not instead of every later purchase. The
        # autonomous loop re-observes the same shop afterward, so affordable packs
        # remain available after the permanent hand-size upgrade is secured.
        gain = max(float(result.normalized_gain), float(voucher.total_advantage), 0.001)
        return replace(
            result,
            action=paint_action,
            source="EARLY_PERSISTENT_CAPACITY",
            total=float(result.hold_baseline) + gain,
            normalized_gain=gain,
            rationale=(
                "Ante 1-2 priority: secure admitted Paint Brush before spending on a Celestial/Planet pack",
                "permanent +1 hand-size capacity improves survival and route flexibility across the remaining run",
                "shop is re-observed after purchase, so affordable booster opportunities may still be taken afterward",
                *voucher.rationale,
                *result.rationale,
            ),
        )

    BuildAwareShopArbiter.decide = decide
    BuildAwareShopArbiter._early_capacity_policy_installed = True
