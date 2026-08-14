from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import BUY_VOUCHER, BalatroAction
from games.balatro.build import BalatroBuildProfiler, BuildProfile
from games.balatro.resource_value import RunResourceValuator
from games.balatro.state import BalatroState


BUY = "BUY"
HOLD = "HOLD"


@dataclass(frozen=True)
class VoucherAcquisitionThresholds:
    """Thresholds owned only by D3 voucher acquisition decisions."""

    minimum_persistent_value: float = 1.0
    minimum_purchase_advantage: float = 0.35
    price_weight: float = 0.20
    interest_weight: float = 1.0
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
        integer_nonnegative = (
            "reserve_target",
            "minimum_money_after",
            "target_ante",
        )
        for name in integer_nonnegative:
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.target_ante) == 0:
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
                "unknown D3 voucher threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class VoucherAcquisitionDecision:
    action: str
    voucher: str
    persistent_value: float
    build_compatibility: float
    horizon_bonus: float
    total_advantage: float
    price: int
    money_after: int
    price_penalty: float
    interest_penalty: float
    reserve_penalty: float
    thresholds: VoucherAcquisitionThresholds
    executable_action: BalatroAction | None = None
    rationale: tuple[str, ...] = ()


class VoucherAcquisitionPolicy:
    """D3 persistent voucher buy-vs-save policy with an explicit HOLD baseline.

    Voucher value is intentionally run-wide: persistent utility, current BuildProfile
    compatibility and remaining-run horizon are scored before D14 money/interest/
    reserve costs are subtracted. D3 owns its admission thresholds independently of
    ordinary Joker, consumable, booster and generic shop-item thresholds.
    """

    _PERSISTENT_VALUE = {
        "Antimatter": 10.0,
        "Palette": 8.0,
        "Nacho Tong": 8.0,
        "Liquidation": 7.0,
        "Observatory": 7.0,
        "Retcon": 7.0,
        "Recyclomancy": 6.5,
        "Money Tree": 6.0,
        "Overstock Plus": 6.0,
        "Reroll Glut": 6.0,
        "Glow Up": 6.0,
        "Paint Brush": 7.0,
        "Grabber": 7.0,
        "Wasteful": 5.5,
        "Crystal Ball": 5.0,
        "Clearance Sale": 5.0,
        "Telescope": 5.0,
        "Director's Cut": 5.0,
        "Petroglyph": 5.0,
        "Tarot Tycoon": 5.0,
        "Planet Tycoon": 5.0,
        "Hieroglyph": 4.0,
        "Overstock": 4.0,
        "Reroll Surplus": 4.0,
        "Hone": 4.0,
        "Illusion": 4.0,
        "Seed Money": 3.0,
        "Tarot Merchant": 3.0,
        "Planet Merchant": 3.0,
        "Magic Trick": 2.5,
        "Blank": 0.5,
    }

    def __init__(
        self,
        thresholds: VoucherAcquisitionThresholds | None = None,
        *,
        profiler: BalatroBuildProfiler | None = None,
        resource_valuator: RunResourceValuator | None = None,
    ) -> None:
        self.thresholds = thresholds or VoucherAcquisitionThresholds()
        self.profiler = profiler or BalatroBuildProfiler()
        self.resource_valuator = resource_valuator or RunResourceValuator()

    def decide(
        self,
        state: BalatroState,
        voucher: object,
    ) -> VoucherAcquisitionDecision:
        if state.phase != "SHOP":
            raise ValueError("D3 voucher acquisition requires SHOP phase")

        label = self._label(voucher)
        price = self._price(voucher)
        money = max(0, int(state.money))
        money_after = money - price
        persistent_value = self._persistent_value(label)
        profile = self.profiler.profile(state)
        compatibility, compatibility_notes = self._build_compatibility(
            state,
            profile,
            label,
        )

        horizon = self.resource_valuator.horizon_value(
            state,
            target_ante=self.thresholds.target_ante,
        )
        horizon_bonus = min(
            self.thresholds.maximum_horizon_bonus,
            persistent_value
            * self.thresholds.remaining_ante_weight
            * horizon.total,
        )

        resource_cost = self.resource_valuator.money_spend_cost(
            money=money,
            spend=price,
            price_weight=self.thresholds.price_weight,
            interest_weight=self.thresholds.interest_weight,
            reserve_target=self.thresholds.reserve_target,
            reserve_weight=self.thresholds.reserve_weight,
        )
        total_advantage = (
            persistent_value
            + compatibility
            + horizon_bonus
            - resource_cost.total
        )

        notes = [
            f"D3 voucher={label}",
            f"persistent_value={persistent_value:.3f}",
            f"build_compatibility={compatibility:.3f}",
            f"horizon_bonus={horizon_bonus:.3f}",
            f"price=${price}",
            f"money_after=${money_after}",
            f"price_penalty={resource_cost.direct:.3f}",
            f"interest_penalty={resource_cost.interest:.3f}",
            f"reserve_penalty={resource_cost.reserve:.3f}",
            f"total_advantage={total_advantage:.3f}",
            (
                "minimum_purchase_advantage="
                f"{self.thresholds.minimum_purchase_advantage:.3f}"
            ),
            *compatibility_notes,
            *horizon.notes,
            *resource_cost.notes,
        ]

        reason: str | None = None
        if price > money:
            reason = "voucher is unaffordable"
        elif persistent_value < self.thresholds.minimum_persistent_value:
            reason = (
                f"persistent value {persistent_value:.3f} below "
                f"minimum {self.thresholds.minimum_persistent_value:.3f}"
            )
        elif money_after < self.thresholds.minimum_money_after:
            reason = (
                f"money after ${money_after} below D3 minimum "
                f"${self.thresholds.minimum_money_after}"
            )
        elif total_advantage <= self.thresholds.minimum_purchase_advantage:
            reason = (
                f"advantage {total_advantage:.3f} does not exceed "
                f"threshold {self.thresholds.minimum_purchase_advantage:.3f}"
            )

        if reason is not None:
            return VoucherAcquisitionDecision(
                action=HOLD,
                voucher=label,
                persistent_value=persistent_value,
                build_compatibility=compatibility,
                horizon_bonus=horizon_bonus,
                total_advantage=total_advantage,
                price=price,
                money_after=money_after,
                price_penalty=resource_cost.direct,
                interest_penalty=resource_cost.interest,
                reserve_penalty=resource_cost.reserve,
                thresholds=self.thresholds,
                rationale=tuple([*notes, f"D3 decision=HOLD: {reason}"]),
            )

        action = BalatroAction(BUY_VOUCHER, target=voucher)
        return VoucherAcquisitionDecision(
            action=BUY,
            voucher=label,
            persistent_value=persistent_value,
            build_compatibility=compatibility,
            horizon_bonus=horizon_bonus,
            total_advantage=total_advantage,
            price=price,
            money_after=money_after,
            price_penalty=resource_cost.direct,
            interest_penalty=resource_cost.interest,
            reserve_penalty=resource_cost.reserve,
            thresholds=self.thresholds,
            executable_action=action,
            rationale=tuple(
                [
                    *notes,
                    (
                        "D3 decision=BUY: advantage "
                        f"{total_advantage:.3f} exceeds threshold "
                        f"{self.thresholds.minimum_purchase_advantage:.3f}"
                    ),
                ]
            ),
        )

    def _build_compatibility(
        self,
        state: BalatroState,
        profile: BuildProfile,
        label: str,
    ) -> tuple[float, tuple[str, ...]]:
        bonus = 0.0
        notes: list[str] = []

        if label == "Antimatter":
            if profile.free_joker_slots <= 0:
                bonus += 2.0
                notes.append("capacity fit: Joker row is full")
            elif profile.free_joker_slots == 1:
                bonus += 0.5
                notes.append("capacity fit: only one Joker slot remains")

        if label == "Crystal Ball":
            if profile.free_consumable_slots <= 0:
                bonus += 1.5
                notes.append("capacity fit: consumable row is full")
            elif profile.free_consumable_slots == 1:
                bonus += 0.5
                notes.append("capacity fit: only one consumable slot remains")

        if label in {"Seed Money", "Money Tree"}:
            interest_bank = min(25, max(0, int(profile.money)))
            economy_bonus = interest_bank / 25.0
            bonus += economy_bonus
            notes.append(
                f"economy fit: current cash ${profile.money} bonus={economy_bonus:.3f}"
            )

        if label in {"Grabber", "Nacho Tong"}:
            hands = max(0, int(getattr(state, "hands_remaining", 0)))
            if hands <= 2:
                bonus += 0.5
                notes.append(f"resource fit: hands_remaining={hands}")

        if label in {"Wasteful", "Recyclomancy"}:
            discards = max(0, int(getattr(state, "discards_remaining", 0)))
            if discards <= 1:
                bonus += 0.35
                notes.append(f"resource fit: discards_remaining={discards}")

        return bonus, tuple(notes)

    def _persistent_value(self, label: str) -> float:
        return self._PERSISTENT_VALUE.get(label, 4.5)

    @staticmethod
    def _label(voucher: object) -> str:
        if isinstance(voucher, dict):
            value = (
                voucher.get("label")
                or voucher.get("name")
                or voucher.get("center")
                or "UNKNOWN"
            )
        else:
            value = (
                getattr(voucher, "label", None)
                or getattr(voucher, "name", None)
                or getattr(voucher, "center", None)
                or type(voucher).__name__
            )
        return str(value)

    @staticmethod
    def _price(voucher: object) -> int:
        if isinstance(voucher, dict):
            value = voucher.get("price", voucher.get("cost", 0))
        else:
            value = getattr(voucher, "price", getattr(voucher, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0
