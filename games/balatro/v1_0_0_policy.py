from __future__ import annotations

"""Balatro v1.0.0 deterministic shop transaction corrections.

The surviving release-layer rules are independent of the retired categorical
strategy architecture:

* an admitted Clearance Sale is bought before other paid development;
* a Joker replacement remains a two-checkpoint committed transaction: sell,
  re-observe, then buy the exact visible Joker that justified the sale.

No rule uses hidden RNG state, future shop/draw ordering, or legacy strategy tiers.
"""

from games.balatro.actions import BUY_JOKER, BUY_VOUCHER, BalatroAction
from games.balatro.shop_arbiter import BuildAwareShopArbiter, ShopArbiterDecision


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_label(item: object) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "center", None)
        or type(item).__name__
    )


def _item_identity(item: object) -> tuple[object | None, str, str]:
    return (
        getattr(item, "live_id", None),
        _normalize(getattr(item, "center", "")),
        _normalize(_item_label(item)),
    )


def _matches_identity(item: object, identity: tuple[object | None, str, str]) -> bool:
    live_id, center, label = identity
    item_live_id, item_center, item_label = _item_identity(item)
    if live_id is not None and item_live_id == live_id:
        return True
    if center and item_center == center:
        return True
    return bool(label and item_label == label)


def _price(item: object) -> int:
    value = getattr(item, "price", getattr(item, "cost", 0))
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _free_joker_slots(state) -> int:
    return max(
        0,
        int(getattr(state, "joker_slots", 5) or 5)
        - len(getattr(state, "jokers", ()) or ()),
    )


def install_v1_0_0_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_v1_0_0_policy_installed", False):
        return

    original_decide = BuildAwareShopArbiter.decide

    def decide(self, state, visible_actions, *, reroll_cost: int | None):
        hold = float(self.shop_policy.hold_bias)

        pending = getattr(self, "_v1_0_0_pending_replacement", None)
        if pending is not None:
            target = next(
                (
                    joker
                    for joker in getattr(state, "shop_jokers", ()) or ()
                    if _matches_identity(joker, pending["identity"])
                ),
                None,
            )
            if (
                target is not None
                and _free_joker_slots(state) > 0
                and int(getattr(state, "money", 0) or 0) >= _price(target)
            ):
                self._v1_0_0_pending_replacement = None
                gain = max(0.001, float(pending.get("normalized_gain", 0.001)))
                return ShopArbiterDecision(
                    action=BalatroAction(BUY_JOKER, target=target),
                    source="JOKER_BUY",
                    total=hold + gain,
                    hold_baseline=hold,
                    normalized_gain=gain,
                    rationale=(
                        "v1.0.0 committed Joker replacement transaction",
                        f"complete purchase of {_item_label(target)} before packs, rerolls, vouchers, or END_SHOP",
                        "the preceding sale is not allowed to become an orphan sale after a fresh shop replan",
                    ),
                )
            self._v1_0_0_pending_replacement = None

        clearance_action = next(
            (
                action
                for action in visible_actions
                if action.name == BUY_VOUCHER
                and _normalize(_item_label(action.target)) == "clearancesale"
            ),
            None,
        )
        if clearance_action is not None:
            ranked = self.shop_policy.rank_actions(state, [clearance_action])
            if ranked and float(ranked[0].total) > hold:
                score = ranked[0]
                return ShopArbiterDecision(
                    action=clearance_action,
                    source="DETERMINISTIC",
                    total=float(score.total),
                    hold_baseline=hold,
                    normalized_gain=max(0.0, float(score.total) - hold),
                    deterministic=score,
                    rationale=(
                        "v1.0.0 shop ordering: admitted Clearance Sale precedes other paid development",
                        "buying the permanent discount first reduces the cost of later shop purchases in the same and future shops",
                        *score.notes,
                    ),
                )

        result = original_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        if result.source == "JOKER_REPLACE_SELL" and result.joker is not None:
            candidate_name = str(result.joker.candidate)
            candidate = next(
                (
                    joker
                    for joker in getattr(state, "shop_jokers", ()) or ()
                    if type(joker).__name__ == candidate_name
                ),
                None,
            )
            if candidate is not None:
                self._v1_0_0_pending_replacement = {
                    "identity": _item_identity(candidate),
                    "normalized_gain": float(result.normalized_gain),
                }
        return result

    BuildAwareShopArbiter.decide = decide
    BuildAwareShopArbiter._v1_0_0_policy_installed = True
