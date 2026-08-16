from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True)
class ResourceValueBreakdown:
    """Explain one marginal current-run resource value on a shared utility scale."""

    total: float
    direct: float = 0.0
    interest: float = 0.0
    reserve: float = 0.0
    survival: float = 0.0
    slot: float = 0.0
    horizon: float = 0.0
    notes: tuple[str, ...] = ()


class RunResourceValuator:
    """Shared marginal utility model for finite Balatro run resources.

    The scale is deliberately policy-facing rather than a claim about literal chip
    or dollar equivalence. Each method exposes its component terms so callers can
    compare resource tradeoffs without duplicating threshold arithmetic.
    """

    INTEREST_STEP = 5
    INTEREST_CAP = 5

    @classmethod
    def interest_value(cls, money: int) -> int:
        money = max(0, int(money))
        return min(cls.INTEREST_CAP, money // cls.INTEREST_STEP)

    def money_transaction_cost(
        self,
        *,
        money: int,
        net_spend: int,
        price_weight: float = 1.0,
        interest_weight: float = 1.0,
        reserve_target: int = 5,
        reserve_weight: float = 1.0,
    ) -> ResourceValueBreakdown:
        """Return shared utility cost for a signed current-money transaction.

        Positive ``net_spend`` spends cash; negative values represent deterministic
        sale credit received as part of the same semantic transaction. Direct and
        interest terms may therefore be negative benefits. Reserve value remains a
        one-way safety penalty: recovering reserve headroom does not create an extra
        reward beyond the cash/interest benefit already represented here.
        """
        money = max(0, int(money))
        net_spend = int(net_spend)
        reserve_target = max(0, int(reserve_target))
        money_after = money - net_spend
        if money_after < 0:
            return ResourceValueBreakdown(
                total=inf,
                direct=inf,
                notes=(
                    f"unaffordable net_spend=${net_spend} money=${money}",
                ),
            )

        direct = float(price_weight) * net_spend
        interest_steps_lost = (
            self.interest_value(money) - self.interest_value(money_after)
        )
        interest = float(interest_weight) * interest_steps_lost
        reserve_before = max(0, reserve_target - money)
        reserve_after = max(0, reserve_target - money_after)
        reserve_delta = max(0, reserve_after - reserve_before)
        reserve = float(reserve_weight) * reserve_delta
        total = direct + interest + reserve
        return ResourceValueBreakdown(
            total=total,
            direct=direct,
            interest=interest,
            reserve=reserve,
            notes=(
                f"money=${money}->${money_after}",
                f"net_spend=${net_spend}",
                f"interest_steps_lost={interest_steps_lost}",
                f"incremental_reserve_shortfall={reserve_delta}",
            ),
        )

    def money_spend_cost(
        self,
        *,
        money: int,
        spend: int,
        price_weight: float = 1.0,
        interest_weight: float = 1.0,
        reserve_target: int = 5,
        reserve_weight: float = 1.0,
    ) -> ResourceValueBreakdown:
        """Return marginal utility forfeited by spending money now."""
        return self.money_transaction_cost(
            money=money,
            net_spend=max(0, int(spend)),
            price_weight=price_weight,
            interest_weight=interest_weight,
            reserve_target=reserve_target,
            reserve_weight=reserve_weight,
        )

    def slot_opportunity_cost(
        self,
        *,
        occupied: int,
        capacity: int,
        last_slot_penalty: float,
        penultimate_slot_penalty: float = 0.0,
        weight: float = 1.0,
        resource: str = "slot",
    ) -> ResourceValueBreakdown:
        """Value the option space consumed by taking one currently open slot."""
        occupied = max(0, int(occupied))
        capacity = max(0, int(capacity))
        open_before = max(0, capacity - occupied)
        if open_before <= 1:
            base = float(last_slot_penalty)
            tier = "last"
        elif open_before == 2:
            base = float(penultimate_slot_penalty)
            tier = "penultimate"
        else:
            base = 0.0
            tier = "roomy"
        slot = max(0.0, float(weight) * base)
        return ResourceValueBreakdown(
            total=slot,
            slot=slot,
            notes=(
                f"resource={resource}",
                f"occupied={occupied}/{capacity}",
                f"slot_tier={tier}",
            ),
        )

    def hand_value(self, state) -> ResourceValueBreakdown:
        """Marginal value of one additional hand under current survival pressure."""
        pressure = self._survival_pressure(state)
        hands = max(0, int(getattr(state, "hands_remaining", 0)))
        scarcity = 1.0 / max(1, hands)
        direct = 1.0
        survival = pressure * (1.0 + scarcity)
        total = direct + survival
        return ResourceValueBreakdown(
            total=total,
            direct=direct,
            survival=survival,
            notes=(
                f"survival_pressure={pressure:.3f}",
                f"hands_remaining={hands}",
                f"hand_scarcity={scarcity:.3f}",
            ),
        )

    def discard_value(self, state) -> ResourceValueBreakdown:
        """Marginal value of one additional discard under current survival pressure."""
        pressure = self._survival_pressure(state)
        discards = max(0, int(getattr(state, "discards_remaining", 0)))
        scarcity = 1.0 / max(1, discards)
        direct = 0.5
        survival = pressure * (0.5 + 0.5 * scarcity)
        total = direct + survival
        return ResourceValueBreakdown(
            total=total,
            direct=direct,
            survival=survival,
            notes=(
                f"survival_pressure={pressure:.3f}",
                f"discards_remaining={discards}",
                f"discard_scarcity={scarcity:.3f}",
            ),
        )

    def horizon_value(
        self,
        state,
        *,
        target_ante: int = 8,
        weight: float = 1.0,
    ) -> ResourceValueBreakdown:
        """Value remaining run horizon, which makes persistent effects worth more early."""
        ante = max(0, int(getattr(state, "ante", 0)))
        target_ante = max(1, int(target_ante))
        remaining = max(0, target_ante - ante)
        normalized = remaining / target_ante
        horizon = max(0.0, float(weight) * normalized)
        return ResourceValueBreakdown(
            total=horizon,
            horizon=horizon,
            notes=(
                f"ante={ante}",
                f"target_ante={target_ante}",
                f"remaining_antes={remaining}",
            ),
        )

    @staticmethod
    def _survival_pressure(state) -> float:
        blind = getattr(state, "blind", None)
        requirement = float(getattr(blind, "requirement", 0.0) or 0.0)
        if requirement <= 0.0:
            return 0.0
        score = max(0.0, float(getattr(state, "score", 0.0) or 0.0))
        remaining = max(0.0, requirement - score)
        return min(1.0, remaining / requirement)
