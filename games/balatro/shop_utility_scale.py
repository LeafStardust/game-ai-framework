from __future__ import annotations

from dataclasses import dataclass

from games.balatro.discovery import bounded_discovery_tiebreak, is_undiscovered
from games.balatro.joker_edition import joker_has_negative_edition
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
        self.resource_valuator: RunResourceValuator = getattr(
            shop_policy,
            "resource_valuator",
            None,
        ) or RunResourceValuator()
        self.price_weight = float(getattr(shop_policy, "price_weight", 0.35))
        self.interest_weight = float(getattr(shop_policy, "interest_weight", 1.25))
        self.reserve_target = int(getattr(shop_policy, "reserve_target", 5))
        self.reserve_weight = float(getattr(shop_policy, "reserve_weight", 0.45))
        self.last_joker_slot_penalty = float(
            getattr(shop_policy, "last_joker_slot_penalty", 1.5)
        )
        self.penultimate_joker_slot_penalty = float(
            getattr(shop_policy, "penultimate_joker_slot_penalty", 0.5)
        )
        self.last_consumable_slot_penalty = float(
            getattr(shop_policy, "last_consumable_slot_penalty", 0.6)
        )

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

        candidate = getattr(executable, "candidate", None)
        economics = selected.economics
        money_cost = self._money_transaction_cost(
            state,
            int(economics.net_spend),
        )
        replacement = executable.source == "JOKER_REPLACE_SELL"
        slot_cost = 0.0
        if not replacement and not joker_has_negative_edition(candidate):
            slot_cost = self.resource_valuator.slot_opportunity_cost(
                occupied=len(state.jokers),
                capacity=int(state.joker_slots),
                last_slot_penalty=self.last_joker_slot_penalty,
                penultimate_slot_penalty=self.penultimate_joker_slot_penalty,
                resource="joker",
            ).total

        edition_delta = float(getattr(economics, "edition_delta", 0.0))
        build_gain = float(selected.build_gain)
        resource_cost = float(money_cost.total) + float(slot_cost)
        base_gain = build_gain + edition_delta - resource_cost
        discovery_applied = (
            not replacement
            and base_gain > 0.0
            and is_undiscovered(candidate)
        )
        gain = (
            bounded_discovery_tiebreak(base_gain, candidate)
            if not replacement
            else base_gain
        )
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 shared SHOP resource scale",
                f"D2 build gain={build_gain:.3f}",
                f"D2 edition delta={edition_delta:.3f}",
                f"shared resource cost={resource_cost:.3f}",
                f"bounded discovery tie-break={'applied' if discovery_applied else 'inactive'}",
            ),
        )

    def consumable_gain(self, state, executable) -> ShopNormalizedUtility:
        selected = executable.decision.selected
        if selected is None:
            raise ValueError("D4 normalized utility requires a selected option")

        candidate = getattr(executable, "candidate", None)
        economics = selected.economics
        money_cost = self._money_spend_cost(state, int(economics.price))
        slot_cost = 0.0
        if selected.mode == "BUY":
            slot_cost = self.resource_valuator.slot_opportunity_cost(
                occupied=len(state.consumables),
                capacity=int(state.consumable_slots),
                last_slot_penalty=self.last_consumable_slot_penalty,
                resource="consumable",
            ).total

        immediate_weight = float(
            executable.decision.thresholds.immediate_money_weight
        )
        immediate_value = float(selected.immediate_gain) * immediate_weight
        build_gain = float(selected.build_gain)
        resource_cost = float(money_cost.total) + float(slot_cost)
        base_gain = build_gain + immediate_value - resource_cost
        discovery_applied = base_gain > 0.0 and is_undiscovered(candidate)
        gain = bounded_discovery_tiebreak(base_gain, candidate)
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 shared SHOP resource scale",
                f"D4 build gain={build_gain:.3f}",
                f"D4 immediate value={immediate_value:.3f}",
                f"shared resource cost={resource_cost:.3f}",
                f"bounded discovery tie-break={'applied' if discovery_applied else 'inactive'}",
            ),
        )

    def booster_gain(self, state, recommendation) -> ShopNormalizedUtility:
        price = self._price(recommendation.action.target)
        money_cost = self._money_spend_cost(state, price)
        option_utility = float(recommendation.option_utility)
        resource_cost = float(money_cost.total)
        base_gain = option_utility - resource_cost
        discovery_applied = (
            base_gain > 0.0 and is_undiscovered(recommendation.action.target)
        )
        gain = bounded_discovery_tiebreak(base_gain, recommendation.action.target)
        return ShopNormalizedUtility(
            gain=gain,
            resource_cost=resource_cost,
            notes=(
                "D14 shared SHOP resource scale",
                f"D8 option utility={option_utility:.3f}",
                f"shared resource cost={resource_cost:.3f}",
                f"bounded discovery tie-break={'applied' if discovery_applied else 'inactive'}",
            ),
        )

    def _money_spend_cost(self, state, spend: int):
        return self.resource_valuator.money_spend_cost(
            money=int(state.money),
            spend=spend,
            price_weight=self.price_weight,
            interest_weight=self.interest_weight,
            reserve_target=self.reserve_target,
            reserve_weight=self.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
        )

    def _money_transaction_cost(self, state, net_spend: int):
        return self.resource_valuator.money_transaction_cost(
            money=int(state.money),
            net_spend=net_spend,
            price_weight=self.price_weight,
            interest_weight=self.interest_weight,
            reserve_target=self.reserve_target,
            reserve_weight=self.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
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
