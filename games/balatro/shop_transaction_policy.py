from __future__ import annotations

"""Deterministic shop transaction completion guards.

Joker replacement remains a two-checkpoint committed transaction: sell, re-observe,
then buy the exact visible Joker that justified the sale. This is transaction
integrity, not a competing shop objective.

Ordinary paid development remains under D14's shared cross-family arbitration. In
particular, Campfire fuel is no longer injected after D14 selects END_SHOP/reroll;
if consumable fuel is strategically valuable it must be admitted and compared by
the ordinary consumable/D14 path rather than a synthetic post-arbiter rescue.

Pure Campfire helper functions remain for deterministic regression compatibility;
production arbitration does not call them.
"""

from games.balatro.actions import BUY_JOKER, BalatroAction
from games.balatro.buffoon_booster_expectation_policy import install_buffoon_booster_expectation_policy
from games.balatro.discovery import is_undiscovered
from games.balatro.planet_scaler_authority import has_planet_use_scaler
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


def _free_consumable_slots(state) -> int:
    return max(
        0,
        int(getattr(state, "consumable_slots", 2) or 2)
        - len(getattr(state, "consumables", ()) or ()),
    )


def _campfire_xmult(state) -> float | None:
    values = []
    for joker in tuple(getattr(state, "jokers", ()) or ()):
        if _normalize(_item_label(joker)).removesuffix("joker") != "campfire":
            continue
        try:
            values.append(max(1.0, float(getattr(joker, "x_mult", 1.0) or 1.0)))
        except (TypeError, ValueError):
            values.append(1.0)
    return min(values) if values else None


def _cash_scaler_owned(state) -> bool:
    return any(
        _normalize(_item_label(joker)).removesuffix("joker") in {"bootstraps", "bull"}
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _campfire_fuel_candidate(state):
    """Legacy pure candidate helper; not used by canonical D14 arbitration."""
    x_mult = _campfire_xmult(state)
    if x_mult is None or _free_consumable_slots(state) <= 0:
        return None
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    target = 1.0 + 0.25 * min(3, max(1, ante // 2))
    if x_mult + 1e-12 >= target:
        return None
    money = max(0, int(getattr(state, "money", 0) or 0))
    reserve = 20 if ante >= 5 else 12
    if _cash_scaler_owned(state):
        reserve = max(reserve, 25)
    candidates = []
    for consumable in tuple(getattr(state, "shop_consumables", ()) or ()):
        if is_undiscovered(consumable):
            continue
        price = _price(consumable)
        if price > 3 or money - price < reserve:
            continue
        category = str(getattr(consumable, "category", "") or "").upper()
        name = _normalize(_item_label(consumable))
        if category == "SPECTRAL" or name in {"thehermit", "temperance", "thefool"}:
            continue
        if category == "PLANET" and has_planet_use_scaler(state):
            continue
        priority = 0 if category == "PLANET" else 1
        candidates.append((priority, price, name, consumable))
    return min(candidates, default=(None, None, None, None))[-1]


def _fuel_inventory_index(state, pending) -> int | None:
    """Legacy pure transaction identity helper retained for regression tests."""
    label = str(pending.get("label", ""))
    matches = [
        index
        for index, consumable in enumerate(tuple(getattr(state, "consumables", ()) or ()))
        if _normalize(_item_label(consumable)) == label
    ]
    existing_count = int(pending.get("existing_count", 0) or 0)
    if len(matches) <= existing_count:
        return None
    return matches[-1]


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

    def best_joker_decision(self, state, *, standalone=None):
        recommendation = original_best_joker(
            self,
            state,
            standalone=standalone,
        )
        self._last_exact_joker_candidate = None if recommendation is None else recommendation.candidate
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

        result = original_decide(self, state, visible_actions, reroll_cost=reroll_cost)
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
