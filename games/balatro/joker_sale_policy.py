from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.build import JokerBuildValue, JokerBuildValueEvaluator
from games.balatro.joker import Joker
from games.balatro.joker_policy import HOLD
from games.balatro.resource_value import RunResourceValuator
from games.balatro.state import BalatroState


SELL = "SELL"


@dataclass(frozen=True)
class JokerSaleThresholds:
    """Thresholds owned only by D2 standalone Joker sale decisions.

    The initial policy is deliberately conservative: by default, cash or slot
    pressure may justify selling only Jokers with no positive whole-build value.
    Selling a useful Joker for speculative future value belongs in later D12/D14
    resource arbitration, not this standalone D2 gate.
    """

    minimum_sale_advantage: float = 0.75
    maximum_build_loss: float = 0.0
    minimum_sell_credit: int = 1
    sell_credit_weight: float = 0.35
    interest_gain_weight: float = 1.25
    reserve_recovery_weight: float = 0.45
    reserve_target: int = 5
    full_slot_release_value: float = 1.0

    def __post_init__(self) -> None:
        nonnegative = (
            "minimum_sale_advantage",
            "maximum_build_loss",
            "sell_credit_weight",
            "interest_gain_weight",
            "reserve_recovery_weight",
            "full_slot_release_value",
        )
        for name in nonnegative:
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.minimum_sell_credit) < 0:
            raise ValueError("minimum_sell_credit cannot be negative")
        if int(self.reserve_target) < 0:
            raise ValueError("reserve_target cannot be negative")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "JokerSaleThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D2 Joker sale threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class JokerSaleOption:
    joker_index: int
    joker: str
    build_value: JokerBuildValue
    build_loss: float
    sell_credit: int | None
    money_after: int | None
    cash_value: float
    interest_gain: float
    reserve_recovery: float
    slot_release_value: float
    edition_penalty: float
    total_advantage: float
    eligible: bool
    blocked_reason: str | None = None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class JokerSaleDecision:
    action: str
    selected: JokerSaleOption | None
    options: tuple[JokerSaleOption, ...]
    thresholds: JokerSaleThresholds
    rationale: tuple[str, ...] = ()


class JokerSalePolicy:
    """D2 standalone SELL-vs-HOLD policy over the complete current build."""

    EDITION_RETENTION_VALUE = {
        "FOIL": 0.8,
        "HOLOGRAPHIC": 1.5,
        "POLYCHROME": 2.5,
        "NEGATIVE": 4.0,
    }

    def __init__(
        self,
        thresholds: JokerSaleThresholds | None = None,
        *,
        evaluator: JokerBuildValueEvaluator | None = None,
    ) -> None:
        self.thresholds = thresholds or JokerSaleThresholds()
        self.evaluator = evaluator or JokerBuildValueEvaluator()

    def decide(self, state: BalatroState) -> JokerSaleDecision:
        options = tuple(
            self._score_sale(state, index, joker)
            for index, joker in enumerate(state.jokers)
            if isinstance(joker, Joker)
        )
        ranked = tuple(
            sorted(
                options,
                key=lambda option: (-option.total_advantage, option.joker_index),
            )
        )
        eligible = [
            option
            for option in ranked
            if option.eligible
            and option.total_advantage > self.thresholds.minimum_sale_advantage
        ]
        if not eligible:
            best = ranked[0] if ranked else None
            best_text = f"{best.total_advantage:.3f}" if best is not None else "none"
            return JokerSaleDecision(
                action=HOLD,
                selected=None,
                options=ranked,
                thresholds=self.thresholds,
                rationale=(
                    f"best standalone sale advantage={best_text}; threshold="
                    f"{self.thresholds.minimum_sale_advantage:.3f}",
                ),
            )

        selected = eligible[0]
        return JokerSaleDecision(
            action=SELL,
            selected=selected,
            options=ranked,
            thresholds=self.thresholds,
            rationale=(
                f"sell slot {selected.joker_index} {selected.joker}",
                f"standalone sale advantage={selected.total_advantage:.3f}",
            ),
        )

    def _score_sale(self, state: BalatroState, index: int, joker: Joker) -> JokerSaleOption:
        baseline = copy.deepcopy(state)
        removed = baseline.jokers.pop(index)
        build_value = self.evaluator.evaluate(baseline, removed)
        build_loss = max(0.0, float(build_value.total_gain))
        removal_gain = max(0.0, -float(build_value.total_gain))

        blocked_reason = self._blocked_reason(joker)
        sell_credit = self._sell_value(joker)
        if sell_credit is None:
            blocked_reason = blocked_reason or "public sell value is unavailable"

        money_after = int(state.money) + sell_credit if sell_credit is not None else None
        cash_value = sell_credit * self.thresholds.sell_credit_weight if sell_credit is not None else 0.0
        vouchers = getattr(state, "vouchers", ())
        interest_gain = (
            (
                self._interest(money_after, vouchers=vouchers)
                - self._interest(int(state.money), vouchers=vouchers)
            )
            * self.thresholds.interest_gain_weight
            if money_after is not None
            else 0.0
        )
        reserve_recovery = (
            self._reserve_recovery(int(state.money), money_after)
            * self.thresholds.reserve_recovery_weight
            if money_after is not None
            else 0.0
        )
        slot_release_value = self._slot_release_value(state, joker)
        edition_penalty = self._edition_retention_value(joker)

        total = removal_gain - build_loss + cash_value + interest_gain + reserve_recovery + slot_release_value - edition_penalty
        eligible = (
            blocked_reason is None
            and sell_credit is not None
            and sell_credit >= int(self.thresholds.minimum_sell_credit)
            and build_loss <= self.thresholds.maximum_build_loss
        )

        rationale = [
            f"whole-build retained value={build_value.total_gain:.3f}",
            f"build loss={build_loss:.3f}",
            f"sell credit={self._format_money(sell_credit)}",
            f"cash value={cash_value:.3f}",
            f"interest gain={interest_gain:.3f}",
            f"reserve recovery={reserve_recovery:.3f}",
            f"slot release value={slot_release_value:.3f}",
            f"edition retention penalty={edition_penalty:.3f}",
            f"sale advantage={total:.3f}",
        ]
        if build_loss > self.thresholds.maximum_build_loss:
            rationale.append(f"build loss exceeds maximum={self.thresholds.maximum_build_loss:.3f}")
        if sell_credit is not None and sell_credit < int(self.thresholds.minimum_sell_credit):
            rationale.append(f"sell credit is below minimum=${self.thresholds.minimum_sell_credit}")
        if blocked_reason is not None:
            rationale.append(blocked_reason)

        return JokerSaleOption(
            joker_index=index,
            joker=type(joker).__name__,
            build_value=build_value,
            build_loss=build_loss,
            sell_credit=sell_credit,
            money_after=money_after,
            cash_value=cash_value,
            interest_gain=interest_gain,
            reserve_recovery=reserve_recovery,
            slot_release_value=slot_release_value,
            edition_penalty=edition_penalty,
            total_advantage=total,
            eligible=eligible,
            blocked_reason=blocked_reason,
            rationale=tuple(rationale),
        )

    def _slot_release_value(self, state: BalatroState, joker: Joker) -> float:
        if self._edition_name(joker) == "NEGATIVE":
            return 0.0
        if len(state.jokers) >= int(state.joker_slots):
            return self.thresholds.full_slot_release_value
        return 0.0

    def _reserve_recovery(self, before: int, after: int) -> int:
        target = int(self.thresholds.reserve_target)
        before_shortfall = max(0, target - before)
        after_shortfall = max(0, target - after)
        return max(0, before_shortfall - after_shortfall)

    @staticmethod
    def _blocked_reason(joker: Joker) -> str | None:
        if bool(getattr(joker, "eternal", False)):
            return "Joker is Eternal and cannot be sold"
        if bool(getattr(joker, "unsellable", False)):
            return "Joker is marked unsellable"
        if getattr(joker, "sellable", None) is False:
            return "Joker is marked not sellable"
        if getattr(joker, "can_sell", None) is False:
            return "Joker is marked not sellable"
        ability = getattr(joker, "ability", None)
        if isinstance(ability, Mapping):
            if bool(ability.get("eternal", False)):
                return "Joker is Eternal and cannot be sold"
            if ability.get("sellable") is False:
                return "Joker is marked not sellable"
        return None

    @staticmethod
    def _sell_value(joker: Joker) -> int | None:
        sentinel = object()
        value = getattr(joker, "sell_cost", sentinel)
        if value is sentinel:
            value = getattr(joker, "sell_value", sentinel)
        if value is sentinel:
            return None
        if isinstance(value, dict):
            value = value.get("sell", value.get("value"))
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _interest(money: int, *, vouchers=()) -> int:
        return RunResourceValuator.interest_value(money, vouchers=vouchers)

    def _edition_retention_value(self, joker: Joker) -> float:
        edition = self._edition_name(joker)
        if edition is None:
            return 0.0
        return self.EDITION_RETENTION_VALUE.get(edition, 0.0)

    @staticmethod
    def _edition_name(joker: Joker) -> str | None:
        edition = getattr(joker, "edition", None)
        if isinstance(edition, Mapping):
            for name, enabled in edition.items():
                if enabled:
                    return str(name).upper()
            return None
        if not edition:
            return None
        return str(edition).upper()

    @staticmethod
    def _format_money(value: int | None) -> str:
        return "unavailable" if value is None else f"${value}"
