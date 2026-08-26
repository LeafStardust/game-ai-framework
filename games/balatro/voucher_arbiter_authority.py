from __future__ import annotations

"""Make D3 the voucher authority consumed by D14 shop arbitration.

``BuildAwareShopArbiter`` asks ``BalatroShopPolicy.rank_actions`` for deterministic
shop actions. Historically that meant visible vouchers bypassed the dedicated D3
``VoucherAcquisitionPolicy`` entirely and were scored by the older generic voucher
heuristics with child-owned money coefficients.

This adapter keeps the existing D14 interface but changes voucher handling only:

* D3 owns BUY/HOLD admission, compatibility, horizon and readiness semantics;
* D14's ``BalatroShopPolicy`` resource coefficients own money/interest/reserve and
  cash-scaling opportunity cost for cross-family comparison;
* the returned ``ShopActionScore.total`` is expressed as ``hold_bias + normalized``
  so the existing D14 ``baseline_gain(total, hold)`` recovers exactly that parent
  normalized value;
* non-voucher actions retain the original ranking path.

No hidden future shops, pack contents, RNG state or draw order are consulted.
"""

from games.balatro.actions import BUY_VOUCHER
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.shop_voucher_policy import (
    BUY,
    VoucherAcquisitionPolicy,
    VoucherAcquisitionThresholds,
)


def _voucher_policy_for_state(state) -> VoucherAcquisitionPolicy:
    try:
        playbook = default_balatro_playbooks().for_state(state)
    except BalatroPlaybookNotFound:
        return VoucherAcquisitionPolicy()
    return VoucherAcquisitionPolicy(
        VoucherAcquisitionThresholds.from_mapping(
            playbook.thresholds_for("D3")
        )
    )


def install_voucher_arbiter_authority() -> None:
    if getattr(BalatroShopPolicy, "_d3_voucher_arbiter_authority_installed", False):
        return

    original_rank_actions = BalatroShopPolicy.rank_actions

    def rank_actions(self, state, actions):
        vouchers = [action for action in actions if action.name == BUY_VOUCHER]
        others = [action for action in actions if action.name != BUY_VOUCHER]
        ranked = list(original_rank_actions(self, state, others)) if others else []
        if not vouchers:
            return ranked

        policy = _voucher_policy_for_state(state)
        for action in vouchers:
            decision = policy.decide(state, action.target)
            if decision.action != BUY or decision.executable_action is None:
                continue

            parent_cost = self.resource_valuator.money_spend_cost(
                money=int(state.money),
                spend=int(decision.price),
                price_weight=float(self.price_weight),
                interest_weight=float(self.interest_weight),
                reserve_target=int(self.reserve_target),
                reserve_weight=float(self.reserve_weight),
                vouchers=getattr(state, "vouchers", ()),
                jokers=getattr(state, "jokers", ()),
            )
            normalized = float(decision.persistent_value) - float(parent_cost.total)
            ranked.append(
                ShopActionScore(
                    action=action,
                    total=float(self.hold_bias) + normalized,
                    item_utility=float(decision.persistent_value),
                    price_penalty=float(parent_cost.direct),
                    interest_penalty=float(parent_cost.interest),
                    reserve_penalty=float(parent_cost.reserve),
                    cash_scaling_penalty=float(parent_cost.cash_scaling),
                    notes=(
                        "D3 owns voucher admission and persistent value",
                        f"D3 persistent value={float(decision.persistent_value):.3f}",
                        f"D14 shared voucher resource cost={float(parent_cost.total):.3f}",
                        f"D14 normalized voucher gain={normalized:.3f}",
                        *tuple(decision.rationale),
                        *tuple(parent_cost.notes),
                    ),
                )
            )

        return sorted(
            ranked,
            key=lambda result: (
                float(result.total),
                result.action.name == "END_SHOP",
            ),
            reverse=True,
        )

    BalatroShopPolicy.rank_actions = rank_actions
    BalatroShopPolicy._d3_voucher_arbiter_authority_installed = True
