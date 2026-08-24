from __future__ import annotations

"""Stable economy mechanics extracted from historical batch policies.

This module contains only invariant game-mechanic behavior. It does not rank
strategies, name preferred Joker pairs, assign static Joker weakness, or override
canonical Bond/Build-Health authority.
"""

from games.balatro.actions import (
    BUY_AND_USE_CONSUMABLE,
    BUY_CONSUMABLE,
    END_SHOP,
    SELL_CONSUMABLE,
    BalatroAction,
)
from games.balatro.live.consumable_timing_base import (
    HOLD,
    USE,
    ConsumableTimingRecommendation,
    LiveConsumableTimingPolicy as BaseConsumableTimingPolicy,
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

    original_economy = BaseConsumableTimingPolicy._recommend_economy

    def recommend_economy(self, state, consumable, *, name: str):
        if name != "The Hermit":
            return original_economy(self, state, consumable, name=name)
        money = max(0, int(getattr(state, "money", 0) or 0))
        gain = min(money, 20)
        required = self._required_per_hand(state)
        slots_full = self._consumable_slots_full(state)
        if gain <= 0:
            return self._hold(
                state,
                consumable,
                "Hermit has no positive deterministic money gain",
                immediate_gain=0.0,
            )
        if money >= 10:
            decision = USE
            reason = "Hermit has reached a strong deterministic payout"
        elif slots_full:
            decision = USE
            reason = "full consumable slots plus positive deterministic Hermit gain"
        else:
            decision = HOLD
            reason = "Hermit is below $10, so preserving it can increase deterministic payout"
        return ConsumableTimingRecommendation(
            decision=decision,
            consumable=consumable,
            target=None,
            before_projection=None,
            after_projection=None,
            required_per_hand=required,
            immediate_gain=float(gain),
            rationale=(
                f"{decision}: {reason}",
                f"Hermit money ${money} -> ${money + gain}",
                f"deterministic money gain=${gain}",
                f"consumable slots full={slots_full}",
            ),
        )

    BaseConsumableTimingPolicy._recommend_economy = recommend_economy

    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        money = max(0, int(getattr(state, "money", 0) or 0))

        # Buy-and-use Hermit only when the public deterministic transaction is
        # immediately profitable after paying its shop price.
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
