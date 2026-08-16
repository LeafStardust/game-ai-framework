from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import BUY_VOUCHER
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.shop_utility_scale import ShopUtilityScale
from games.balatro.shop_voucher_policy import (
    BUY as VOUCHER_BUY,
    VoucherAwareBalatroShopPolicy,
)


@dataclass(frozen=True)
class ResourceValuationThresholds:
    """D14 shared finite-resource coefficients for parent SHOP comparison.

    Child layers remain authoritative for admission. D14 owns only the common
    money/interest/reserve/slot scale used after admission so cross-family scores
    stay comparable even when a child layer has different local economics.
    """

    price_weight: float = 0.35
    interest_weight: float = 1.25
    reserve_target: int = 5
    reserve_weight: float = 0.45
    last_joker_slot_penalty: float = 1.5
    penultimate_joker_slot_penalty: float = 0.5
    last_consumable_slot_penalty: float = 0.6

    def __post_init__(self) -> None:
        nonnegative = (
            "price_weight",
            "interest_weight",
            "reserve_weight",
            "last_joker_slot_penalty",
            "penultimate_joker_slot_penalty",
            "last_consumable_slot_penalty",
        )
        for name in nonnegative:
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.reserve_target) < 0:
            raise ValueError("reserve_target cannot be negative")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "ResourceValuationThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D14 resource-valuation threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    @classmethod
    def from_shop_policy(cls, shop_policy) -> "ResourceValuationThresholds":
        return cls(
            price_weight=float(getattr(shop_policy, "price_weight", 0.35)),
            interest_weight=float(getattr(shop_policy, "interest_weight", 1.25)),
            reserve_target=int(getattr(shop_policy, "reserve_target", 5)),
            reserve_weight=float(getattr(shop_policy, "reserve_weight", 0.45)),
            last_joker_slot_penalty=float(
                getattr(shop_policy, "last_joker_slot_penalty", 1.5)
            ),
            penultimate_joker_slot_penalty=float(
                getattr(shop_policy, "penultimate_joker_slot_penalty", 0.5)
            ),
            last_consumable_slot_penalty=float(
                getattr(shop_policy, "last_consumable_slot_penalty", 0.6)
            ),
        )

    def apply_to(self, target) -> None:
        for field in fields(self):
            setattr(target, field.name, getattr(self, field.name))


def _resource_thresholds_for_state(
    state,
    *,
    fallback_policy,
    override: ResourceValuationThresholds | None = None,
) -> ResourceValuationThresholds:
    if override is not None:
        return override
    try:
        block = default_balatro_playbooks().for_state(state).thresholds_for("D14")
    except BalatroPlaybookNotFound:
        return ResourceValuationThresholds.from_shop_policy(fallback_policy)
    return ResourceValuationThresholds.from_mapping(block)


class PlaybookShopUtilityScale(ShopUtilityScale):
    """Existing D14 normalizer with deck/stake-owned resource coefficients."""

    def __init__(
        self,
        shop_policy,
        *,
        thresholds: ResourceValuationThresholds | None = None,
    ) -> None:
        super().__init__(shop_policy)
        self.thresholds = thresholds

    def thresholds_for_state(self, state) -> ResourceValuationThresholds:
        return _resource_thresholds_for_state(
            state,
            fallback_policy=self.shop_policy,
            override=self.thresholds,
        )

    def _apply_state_thresholds(self, state) -> None:
        self.thresholds_for_state(state).apply_to(self)

    def joker_gain(self, state, executable):
        self._apply_state_thresholds(state)
        return super().joker_gain(state, executable)

    def consumable_gain(self, state, executable):
        self._apply_state_thresholds(state)
        return super().consumable_gain(state, executable)

    def booster_gain(self, state, recommendation):
        self._apply_state_thresholds(state)
        return super().booster_gain(state, recommendation)


class PlaybookVoucherAwareBalatroShopPolicy(VoucherAwareBalatroShopPolicy):
    """D3 admission mapped onto the same D14 scale used by the parent arbiter.

    D3 still decides whether a visible Voucher is admissible using its own persistent
    value/economy thresholds. Once admitted, the score returned to D12 is rebuilt
    from D3 persistent value and D14 resource cost so D3 coefficients cannot distort
    cross-family comparison. Applying D14 to this shared shop policy also keeps D11
    reroll economics on the same resource scale during the parent decision.
    """

    def __init__(
        self,
        *args,
        resource_thresholds: ResourceValuationThresholds | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.resource_thresholds = resource_thresholds

    def resource_thresholds_for_state(self, state) -> ResourceValuationThresholds:
        return _resource_thresholds_for_state(
            state,
            fallback_policy=self,
            override=self.resource_thresholds,
        )

    def rank_actions(self, state, actions):
        thresholds = self.resource_thresholds_for_state(state)
        thresholds.apply_to(self)

        voucher_actions = [action for action in actions if action.name == BUY_VOUCHER]
        other_actions = [action for action in actions if action.name != BUY_VOUCHER]
        scores = list(BalatroShopPolicy.rank_actions(self, state, other_actions))

        for action in voucher_actions:
            decision = self.recommend_voucher(state, action.target)
            if decision.action != VOUCHER_BUY or decision.executable_action is None:
                continue
            resource_cost = self.resource_valuator.money_spend_cost(
                money=int(state.money),
                spend=int(decision.price),
                price_weight=float(thresholds.price_weight),
                interest_weight=float(thresholds.interest_weight),
                reserve_target=int(thresholds.reserve_target),
                reserve_weight=float(thresholds.reserve_weight),
                vouchers=getattr(state, "vouchers", ()),
            )
            normalized_advantage = float(decision.persistent_value) - resource_cost.total
            scores.append(
                ShopActionScore(
                    action=action,
                    total=float(self.hold_bias) + normalized_advantage,
                    item_utility=float(decision.persistent_value),
                    price_penalty=resource_cost.direct,
                    interest_penalty=resource_cost.interest,
                    reserve_penalty=resource_cost.reserve,
                    notes=(
                        *decision.rationale,
                        "D14 remaps admitted D3 Voucher onto shared SHOP resource scale",
                        f"D14 resource cost={resource_cost.total:.3f}",
                    ),
                )
            )

        return sorted(
            scores,
            key=lambda result: (
                result.total,
                result.action.name == "END_SHOP",
            ),
            reverse=True,
        )


class PlaybookBuildAwareShopArbiter(BuildAwareShopArbiter):
    """D12 invariant arbiter using the playbook-owned D14 normalization scale.

    D12 intentionally has no independent tuning threshold: child admission belongs
    to D2/D3/D4/D8/D11 and shared finite-resource valuation belongs to D14. Its
    deterministic tie order and free-reroll rule are arbitration invariants.
    """

    def __init__(self, *args, resource_thresholds=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.utility_scale = PlaybookShopUtilityScale(
            self.shop_policy,
            thresholds=resource_thresholds,
        )
