from __future__ import annotations

from dataclasses import dataclass

from games.balatro.resource_value import RunResourceValuator


@dataclass(frozen=True)
class ShopNormalizedUtility:
    """One admitted SHOP option expressed on the parent D14 utility scale."""

    gain: float
    resource_cost: float = 0.0
    notes: tuple[str, ...] = ()


class ShopUtilityScale:
    """Normalize admitted child decisions for cross-family SHOP arbitration.

    Child layers remain authoritative for admission and their own strategic
    thresholds. D12 uses this object only after a child has admitted an option, so
    D2/D4/D8 cannot accidentally change cross-family units by changing their local
    price, interest, reserve, or slot coefficients. Those finite-resource terms are
    recomputed with the single BalatroShopPolicy resource scale also used by
    deterministic purchases and D11 rerolls.
    """

    def __init__(self, shop_policy) -> None:
        self.shop_policy = shop_policy
        self.resource_valuator: RunResourceValuator = shop_policy.resource_valuator

    @staticmethod
    def baseline_gain(total: float, baseline: float) -> ShopNormalizedUtility:
        gain = float(total) - float(baseline)
        return ShopNormalizedUtility(
            gain=gain,
            notes=(
                f"child total={float(total):.3f}",
                f"child no-action baseline={float(baseline):.3f}",
            ),
        )

    def joker_gain(self, state, executable) -> ShopNormalizedUtility:
        selected = executable.decision.selected
        if selected is None:
            raise ValueError("D2 normalized utility requires a selected option")

        economics = selected.economics
        money_cost = self._money_transaction_cost(
            state,
            int(economics.net_spend),
        )
        replacement = executable.source == "JOKER_REPLACE_SELL"
        slot_cost = 0.0
        if not replacement:
            slot_cost = self.resource_valuator.slot_opportunity_cost(
                occupied=len(state.jokers),
                capacity=int(state.joker_slots),
                last_slot_penalty=float(self.shop_policy.last_joker_slot_penalty),
                penultimate_slot_penalty=float(
                    self.shop_policy.penultimate_joker_slot_penalty
                ),
                resource="joker",
            ).total

        edition_delta = float(getattr(economics, "edition_delta", 0.0))
        build_gain = float(selected.build_gain)
        resource_cost = float(money_cost.total) + float(slot_cost)
        gain = build_gain + edition_delta - resource_cost
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 shared SHOP resource scale",
                f"D2 build gain={build_gain:.3f}",
                f"D2 edition delta={edition_delta:.3f}",
                f"shared resource cost={resource_cost:.3f}",
            ),
        )

    def consumable_gain(self, state, executable) -> ShopNormalizedUtility:
        selected = executable.decision.selected
        if selected is None:
            raise ValueError("D4 normalized utility requires a selected option")

        economics = selected.economics
        money_cost = self._money_spend_cost(state, int(economics.price))
        slot_cost = 0.0
        if selected.mode == "BUY":
            slot_cost = self.resource_valuator.slot_opportunity_cost(
                occupied=len(state.consumables),
                capacity=int(state.consumable_slots),
                last_slot_penalty=float(
                    self.shop_policy.last_consumable_slot_penalty
                ),
                resource="consumable",
            ).total

        immediate_weight = float(
            executable.decision.thresholds.immediate_money_weight
        )
        immediate_value = float(selected.immediate_gain) * immediate_weight
        build_gain = float(selected.build_gain)
        resource_cost = float(money_cost.total) + float(slot_cost)
        gain = build_gain + immediate_value - resource_cost
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 shared SHOP resource scale",
                f"D4 build gain={build_gain:.3f}",
                f"D4 immediate value={immediate_value:.3f}",
                f"shared resource cost={resource_cost:.3f}",
            ),
        )

    def booster_gain(self, state, recommendation) -> ShopNormalizedUtility:
        price = self._price(recommendation.action.target)
        money_cost = self._money_spend_cost(state, price)
        option_utility = float(recommendation.option_utility)
        resource_cost = float(money_cost.total)
        gain = option_utility - resource_cost
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 shared SHOP resource scale",
                f"D8 option utility={option_utility:.3f}",
                f"shared resource cost={resource_cost:.3f}",
            ),
        )

    def _money_spend_cost(self, state, spend: int):
        return self.resource_valuator.money_spend_cost(
            money=int(state.money),
            spend=spend,
            price_weight=float(self.shop_policy.price_weight),
            interest_weight=float(self.shop_policy.interest_weight),
            reserve_target=int(self.shop_policy.reserve_target),
            reserve_weight=float(self.shop_policy.reserve_weight),
        )

    def _money_transaction_cost(self, state, net_spend: int):
        return self.resource_valuator.money_transaction_cost(
            money=int(state.money),
            net_spend=net_spend,
            price_weight=float(self.shop_policy.price_weight),
            interest_weight=float(self.shop_policy.interest_weight),
            reserve_target=int(self.shop_policy.reserve_target),
            reserve_weight=float(self.shop_policy.reserve_weight),
        )

    @staticmethod
    def _price(item) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0
