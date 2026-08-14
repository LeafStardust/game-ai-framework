from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import BUY_VOUCHER, BalatroAction
from games.balatro.build.profile import BalatroBuildProfiler
from games.balatro.playbook import (
    BalatroPlaybookNotFound,
    default_balatro_playbooks,
)
from games.balatro.shop_policy import (
    BalatroShopPolicy,
    DefaultShopItemValueEstimator,
    ShopActionScore,
    ShopItemValueEstimator,
)
from games.balatro.state import BalatroState


BUY = "BUY"
HOLD = "HOLD"


@dataclass(frozen=True)
class VoucherAcquisitionThresholds:
    """Thresholds owned only by D3 persistent voucher acquisition.

    Vouchers are permanent run upgrades, so D3 should not share the ordinary
    one-shop item threshold. The generic item estimator still supplies a transparent
    base value; D3 adds run horizon, public build-capacity compatibility and its own
    transaction economics before deciding BUY versus HOLD.
    """

    minimum_persistent_value: float = 1.0
    minimum_purchase_advantage: float = 0.35
    price_weight: float = 0.20
    interest_weight: float = 1.00
    reserve_target: int = 5
    reserve_weight: float = 0.45
    minimum_money_after: int = 5
    target_ante: int = 8
    remaining_ante_weight: float = 0.20
    maximum_horizon_bonus: float = 1.40

    def __post_init__(self) -> None:
        nonnegative = (
            "minimum_persistent_value",
            "minimum_purchase_advantage",
            "price_weight",
            "interest_weight",
            "reserve_weight",
            "remaining_ante_weight",
            "maximum_horizon_bonus",
        )
        for name in nonnegative:
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.reserve_target) < 0:
            raise ValueError("reserve_target cannot be negative")
        if int(self.minimum_money_after) < 0:
            raise ValueError("minimum_money_after cannot be negative")
        if int(self.target_ante) < 1:
            raise ValueError("target_ante must be positive")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "VoucherAcquisitionThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D3 Voucher threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class VoucherAcquisitionDecision:
    action: str
    candidate: str
    executable_action: BalatroAction | None
    base_persistent_value: float
    build_compatibility: float
    horizon_bonus: float
    persistent_value: float
    total_advantage: float
    price: int
    money_after: int
    price_penalty: float
    interest_penalty: float
    reserve_penalty: float
    thresholds: VoucherAcquisitionThresholds
    rationale: tuple[str, ...] = ()


class VoucherAcquisitionPolicy:
    """D3 buy-versus-save policy for one visible persistent Voucher.

    This policy does not predict future shops. It values only the currently visible
    Voucher using public run state, then compares that persistent value against the
    cash, interest and reserve cost of buying it now.
    """

    def __init__(
        self,
        thresholds: VoucherAcquisitionThresholds | None = None,
        *,
        item_value_estimator: ShopItemValueEstimator | None = None,
        profiler: BalatroBuildProfiler | None = None,
    ) -> None:
        self.thresholds = thresholds or VoucherAcquisitionThresholds()
        self.item_value_estimator = (
            item_value_estimator or DefaultShopItemValueEstimator()
        )
        self.profiler = profiler or BalatroBuildProfiler()

    def decide(self, state: BalatroState, candidate: object) -> VoucherAcquisitionDecision:
        if state.phase != "SHOP":
            raise ValueError("D3 voucher policy requires SHOP phase")

        action = BalatroAction(BUY_VOUCHER, target=candidate)
        candidate_name = str(
            getattr(candidate, "label", getattr(candidate, "name", type(candidate).__name__))
        )
        price = self._price(candidate)
        money_after = int(state.money) - price

        if money_after < 0:
            return VoucherAcquisitionDecision(
                action=HOLD,
                candidate=candidate_name,
                executable_action=None,
                base_persistent_value=0.0,
                build_compatibility=0.0,
                horizon_bonus=0.0,
                persistent_value=0.0,
                total_advantage=float("-inf"),
                price=price,
                money_after=money_after,
                price_penalty=0.0,
                interest_penalty=0.0,
                reserve_penalty=0.0,
                thresholds=self.thresholds,
                rationale=(
                    f"D3 unaffordable: costs ${price} with ${state.money} available",
                ),
            )

        base_value, base_notes = self.item_value_estimator.estimate(state, action)
        profile = self.profiler.profile(state)
        compatibility, compatibility_notes = self._build_compatibility(
            state,
            profile,
            candidate_name,
        )
        remaining_antes = max(
            0,
            int(self.thresholds.target_ante) - int(profile.ante),
        )
        horizon_bonus = min(
            float(self.thresholds.maximum_horizon_bonus),
            remaining_antes * float(self.thresholds.remaining_ante_weight),
        )
        persistent_value = float(base_value) + compatibility + horizon_bonus

        price_penalty = price * float(self.thresholds.price_weight)
        interest_penalty = (
            self._interest(int(state.money)) - self._interest(money_after)
        ) * float(self.thresholds.interest_weight)
        reserve_penalty = self._incremental_reserve_shortfall(
            int(state.money),
            money_after,
        ) * float(self.thresholds.reserve_weight)
        total_advantage = (
            persistent_value
            - price_penalty
            - interest_penalty
            - reserve_penalty
        )

        persistent_enough = persistent_value >= float(
            self.thresholds.minimum_persistent_value
        )
        reserve_safe = money_after >= int(self.thresholds.minimum_money_after)
        should_buy = (
            persistent_enough
            and reserve_safe
            and total_advantage > float(self.thresholds.minimum_purchase_advantage)
        )
        decision = BUY if should_buy else HOLD

        rationale = (
            f"D3 voucher={candidate_name}",
            f"D3 base persistent value={float(base_value):.3f}",
            *tuple(str(note) for note in base_notes),
            f"D3 build compatibility={compatibility:.3f}",
            *compatibility_notes,
            f"D3 future-ante horizon={remaining_antes} bonus={horizon_bonus:.3f}",
            f"D3 price penalty={price_penalty:.3f}",
            f"D3 interest penalty={interest_penalty:.3f}",
            f"D3 reserve penalty={reserve_penalty:.3f}",
            f"D3 money after=${money_after} minimum=${self.thresholds.minimum_money_after}",
            f"D3 persistent value={persistent_value:.3f}",
            f"D3 purchase advantage={total_advantage:.3f}",
            (
                "D3 BUY: persistent upgrade clears dedicated value/economy thresholds"
                if should_buy
                else "D3 HOLD: persistent upgrade fails dedicated value/economy thresholds"
            ),
        )

        return VoucherAcquisitionDecision(
            action=decision,
            candidate=candidate_name,
            executable_action=action if should_buy else None,
            base_persistent_value=float(base_value),
            build_compatibility=compatibility,
            horizon_bonus=horizon_bonus,
            persistent_value=persistent_value,
            total_advantage=total_advantage,
            price=price,
            money_after=money_after,
            price_penalty=price_penalty,
            interest_penalty=interest_penalty,
            reserve_penalty=reserve_penalty,
            thresholds=self.thresholds,
            rationale=rationale,
        )

    @staticmethod
    def _build_compatibility(state, profile, label: str) -> tuple[float, tuple[str, ...]]:
        """Return public build-capacity/resource fit without future-shop prediction."""
        if label == "Antimatter":
            pressure = max(0, 2 - int(profile.free_joker_slots))
            value = 1.50 + 0.75 * pressure
            return value, (
                f"D3 Antimatter Joker-capacity pressure={pressure} "
                f"free_slots={profile.free_joker_slots}",
            )

        if label in {"Paint Brush", "Palette"}:
            hand_size = int(getattr(state, "hand_size", 0))
            value = 1.50 + (0.25 if hand_size <= 8 else 0.0)
            return value, (
                f"D3 permanent hand-size capacity current={hand_size}",
            )

        if label in {"Grabber", "Nacho Tong"}:
            return 1.75, ("D3 permanent hands-per-round capacity",)

        if label in {"Wasteful", "Recyclomancy"}:
            return 1.25, ("D3 permanent discards-per-round capacity",)

        if label in {"Seed Money", "Money Tree"}:
            money = int(profile.money)
            value = min(1.50, max(0.0, money - 10) * 0.05)
            return value, (
                f"D3 interest-engine compatibility current_money=${money}",
            )

        if label == "Blank":
            return 0.0, ("D3 Blank has no current build-capacity effect",)

        return 0.0, ("D3 no explicit build-capacity adjustment",)

    @staticmethod
    def _price(item) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _interest(money: int) -> int:
        # D14 later generalizes voucher-modified caps/rates. D3 uses the current
        # ordinary public interest schedule only to avoid pretending cash is free.
        return min(5, max(0, int(money)) // 5)

    def _incremental_reserve_shortfall(self, before: int, after: int) -> int:
        before_shortfall = max(0, int(self.thresholds.reserve_target) - before)
        after_shortfall = max(0, int(self.thresholds.reserve_target) - after)
        return max(0, after_shortfall - before_shortfall)


class VoucherAwareBalatroShopPolicy(BalatroShopPolicy):
    """BalatroShopPolicy adapter that makes D3 authoritative for Vouchers.

    Non-voucher actions keep the existing shop policy. Voucher candidates are first
    admitted/rejected by D3; admitted advantages are mapped back onto the parent's
    existing hold-baseline scale so BuildAwareShopArbiter needs no second voucher
    implementation.
    """

    def __init__(
        self,
        item_value_estimator: ShopItemValueEstimator | None = None,
        *,
        voucher_policy: VoucherAcquisitionPolicy | None = None,
        **kwargs,
    ) -> None:
        super().__init__(item_value_estimator=item_value_estimator, **kwargs)
        self.voucher_policy = voucher_policy

    def recommend_voucher(
        self,
        state: BalatroState,
        candidate: object,
    ) -> VoucherAcquisitionDecision:
        policy = self._voucher_policy_for_state(state)
        return policy.decide(state, candidate)

    def rank_actions(
        self,
        state: BalatroState,
        actions: list[BalatroAction],
    ) -> list[ShopActionScore]:
        voucher_actions = [action for action in actions if action.name == BUY_VOUCHER]
        other_actions = [action for action in actions if action.name != BUY_VOUCHER]
        scores = list(super().rank_actions(state, other_actions))

        for action in voucher_actions:
            decision = self.recommend_voucher(state, action.target)
            if decision.action != BUY or decision.executable_action is None:
                continue
            scores.append(
                ShopActionScore(
                    action=action,
                    total=float(self.hold_bias) + float(decision.total_advantage),
                    item_utility=decision.persistent_value,
                    price_penalty=decision.price_penalty,
                    interest_penalty=decision.interest_penalty,
                    reserve_penalty=decision.reserve_penalty,
                    notes=decision.rationale,
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

    def _voucher_policy_for_state(self, state: BalatroState) -> VoucherAcquisitionPolicy:
        if self.voucher_policy is not None:
            return self.voucher_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            thresholds = VoucherAcquisitionThresholds()
        else:
            thresholds = VoucherAcquisitionThresholds.from_mapping(
                playbook.strategy.get("decision_thresholds", {}).get(
                    "voucher_acquisition",
                    {},
                )
            )

        return VoucherAcquisitionPolicy(
            thresholds,
            item_value_estimator=self.item_value_estimator,
        )
