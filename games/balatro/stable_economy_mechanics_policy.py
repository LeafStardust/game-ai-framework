from __future__ import annotations

"""Stable shop transaction mechanics extracted from historical batch policies.

Only invariant SHOP transaction behavior remains here. Held-consumable timing is
owned by ``live.consumable_timing_base``/D5 and must not be monkey-patched from a
registration layer.
"""

from games.balatro.actions import (
    BUY_AND_USE_CONSUMABLE,
    BUY_CONSUMABLE,
    END_SHOP,
    SELL_CONSUMABLE,
    BalatroAction,
)
from games.balatro.shop_arbiter import BuildAwareShopArbiter, ShopArbiterDecision


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _label(item: object) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "center", None)
        or type(item).__name__
    )


def _token(item: object) -> str:
    return _normalize(type(item).__name__)


def _price(item: object) -> int:
    value = getattr(item, "price", getattr(item, "cost", 0))
    if isinstance(value, dict):
        value = value.get("buy", 0)
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _is_negative(item: object) -> bool:
    return _normalize(getattr(item, "edition", "")) == "negative"


def _shop_decision(self, *, state, action, source: str, gain: float, rationale: tuple[str, ...]):
    hold = float(self.shop_policy.hold_bias)
    gain = max(0.001, float(gain))
    consumable_decision = None
    if source in {"CONSUMABLE_BUY", "CONSUMABLE_BUY_AND_USE"} and action.target is not None:
        try:
            consumable_decision = self._consumable_policy_for_state(state).decide(state, action.target)
        except (AttributeError, TypeError, ValueError):
            consumable_decision = None
    return ShopArbiterDecision(
        action=action,
        source=source,
        total=hold + gain,
        hold_baseline=hold,
        normalized_gain=gain,
        consumable=consumable_decision,
        rationale=rationale,
    )


def install_stable_economy_mechanics_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_stable_economy_mechanics_installed", False):
        return

    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        money = max(0, int(getattr(state, "money", 0) or 0))

        # Buy-and-use Hermit only when the public deterministic transaction is
        # immediately profitable after paying its shop price. D5 itself remains
        # authoritative for held Hermit USE/HOLD timing.
        for consumable in getattr(state, "shop_consumables", ()) or ():
            if _normalize(_label(consumable)) not in {"thehermit", "hermit"}:
                continue
            price = _price(consumable)
            money_after = money - price
            if money_after < 0:
                continue
            payout = min(money_after, 20)
            final_money = money_after + payout
            net_profit = final_money - money
            if net_profit > 0:
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(BUY_AND_USE_CONSUMABLE, target=consumable),
                    source="CONSUMABLE_BUY_AND_USE",
                    gain=float(net_profit),
                    rationale=(
                        "Hermit deterministic profitable Buy & Use",
                        f"cash ${money} -> ${final_money} after ${price} purchase and +${payout} payout",
                    ),
                )

        has_perkeo = any(_token(joker) == "perkeojoker" for joker in getattr(state, "jokers", ()) or ())
        if has_perkeo:
            held = list(getattr(state, "consumables", ()) or ())
            for index, consumable in enumerate(held):
                if not _is_negative(consumable):
                    continue
                name = _normalize(_label(consumable))
                if any(other is not consumable and _normalize(_label(other)) == name for other in held):
                    return _shop_decision(
                        self,
                        state=state,
                        action=BalatroAction(SELL_CONSUMABLE, target=index),
                        source="PERKEO_CASH",
                        gain=max(1.0, float(getattr(consumable, "sell_cost", 1) or 1)),
                        rationale=(
                            "Perkeo stable mechanic: monetize surplus Negative duplicate",
                            f"retain another {_label(consumable)} as the next Perkeo seed",
                        ),
                    )

        result = original_shop_decide(self, state, visible_actions, reroll_cost=reroll_cost)

        if has_perkeo and not getattr(state, "consumables", ()) and result.action.name == END_SHOP:
            affordable = [
                consumable
                for consumable in getattr(state, "shop_consumables", ()) or ()
                if _price(consumable) <= max(0, money - 5)
            ]
            if affordable:
                seed = min(affordable, key=lambda item: (_price(item), _normalize(_label(item))))
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(BUY_CONSUMABLE, target=seed),
                    source="PERKEO_SEED",
                    gain=1.0,
                    rationale=(
                        "Perkeo stable mechanic: do not leave shop with an empty consumable area when a safe seed is available",
                        f"buy {_label(seed)} for ${_price(seed)} while retaining $5 cash reserve",
                    ),
                )

        return result

    BuildAwareShopArbiter.decide = shop_decide
    BuildAwareShopArbiter._stable_economy_mechanics_installed = True
