from __future__ import annotations

"""Deterministic shop transaction completion guards.

Joker replacement remains a two-checkpoint committed transaction: sell, re-observe,
then buy the exact visible Joker that justified the sale. This is transaction
integrity, not a competing shop objective.

Ordinary paid development remains under D14's shared cross-family arbitration. In
particular, Campfire fuel is no longer injected after D14 selects END_SHOP/reroll;
if consumable fuel is strategically valuable it must be admitted and compared by
the ordinary consumable/D14 path rather than a synthetic post-arbiter rescue.

No rule uses hidden RNG state, future shop/draw ordering, or legacy strategy tiers.
"""

from games.balatro.actions import BUY_JOKER, BalatroAction
from games.balatro.buffoon_booster_expectation_policy import install_buffoon_booster_expectation_policy
from games.balatro.reroll_joker_expectation_policy import install_reroll_joker_expectation_policy
from games.balatro.reroll_planet_expectation_policy import install_reroll_planet_expectation_policy
from games.balatro.reroll_tarot_guard_policy import install_reroll_tarot_guard_policy
from games.balatro.shop_arbiter import BuildAwareShopArbiter, ShopArbiterDecision
from games.balatro.voucher_arbiter_authority import install_voucher_arbiter_authority


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


def install_shop_transaction_policy() -> None:
    install_voucher_arbiter_authority()
    install_reroll_joker_expectation_policy()
    install_reroll_planet_expectation_policy()
    install_reroll_tarot_guard_policy()
    install_buffoon_booster_expectation_policy()
    if getattr(BuildAwareShopArbiter, "_shop_transaction_policy_installed", False):
        return

    original_best_joker = BuildAwareShopArbiter._best_joker_decision
    original_decide = BuildAwareShopArbiter.decide

    def best_joker_decision(self, state):
        recommendation = original_best_joker(self, state)
        self._last_exact_joker_candidate = (
            None if recommendation is None else recommendation.candidate
        )
        return recommendation

    def decide(self, state, visible_actions, *, reroll_cost: int | None):
        hold = float(self.shop_policy.hold_bias)
        self._last_exact_joker_candidate = None

        pending = getattr(self, "_pending_committed_replacement", None)
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
                self._pending_committed_replacement = None
                gain = max(0.001, float(pending.get("normalized_gain", 0.001)))
                return ShopArbiterDecision(
                    action=BalatroAction(BUY_JOKER, target=target),
                    source="JOKER_BUY",
                    total=hold + gain,
                    hold_baseline=hold,
                    normalized_gain=gain,
                    rationale=(
                        "committed Joker replacement transaction",
                        f"complete purchase of {_item_label(target)} before packs, rerolls, vouchers, or END_SHOP",
                        "the preceding sale is not allowed to become an orphan sale after a fresh shop replan",
                    ),
                )
            self._pending_committed_replacement = None

        result = original_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        if result.source == "JOKER_REPLACE_SELL" and result.joker is not None:
            candidate = getattr(self, "_last_exact_joker_candidate", None)
            if candidate is not None:
                self._pending_committed_replacement = {
                    "identity": _item_identity(candidate),
                    "normalized_gain": float(result.normalized_gain),
                }
        return result

    BuildAwareShopArbiter._best_joker_decision = best_joker_decision
    BuildAwareShopArbiter.decide = decide
    BuildAwareShopArbiter._shop_transaction_policy_installed = True
