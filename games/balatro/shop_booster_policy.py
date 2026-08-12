from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.build import BalatroBuildProfiler
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class ShopBoosterThresholds:
    """Dedicated B5 thresholds for unopened booster option value.

    Values are conservative option values for entering a pack family. They do not
    estimate the identity, rarity, edition, or other hidden contents of the pack.
    """

    celestial_base: float = 4.0
    buffoon_base: float = 4.5
    standard_base: float = 3.0
    jumbo_bonus: float = 0.75
    mega_bonus: float = 1.25
    hand_investment_weight: float = 0.35
    max_hand_investment_bonus: float = 2.0
    free_joker_slot_bonus: float = 0.35
    max_free_joker_slot_bonus: float = 1.0
    minimum_margin: float = 0.25


@dataclass(frozen=True)
class ShopBoosterRecommendation:
    decision: str
    action: BalatroAction
    family: str | None
    variant: str | None
    total: float
    option_utility: float = 0.0
    price_penalty: float = 0.0
    interest_penalty: float = 0.0
    reserve_penalty: float = 0.0
    rationale: tuple[str, ...] = ()


class BuildAwareShopBoosterPolicy:
    """Value unopened boosters without predicting their future random contents.

    Only pack families whose post-open autonomous path is currently safe are
    admitted. Arcana/Spectral remain visible but fail closed until their targeted
    pack-effect execution is validated.
    """

    AUTONOMOUS_SAFE_FAMILIES = frozenset({"CELESTIAL", "BUFFOON", "STANDARD"})

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        build_profiler: BalatroBuildProfiler | None = None,
        thresholds: ShopBoosterThresholds | None = None,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.build_profiler = build_profiler or BalatroBuildProfiler()
        self.thresholds = thresholds or ShopBoosterThresholds()

    def recommend(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> ShopBoosterRecommendation:
        if state.phase != "SHOP":
            raise ValueError("booster policy requires SHOP phase")
        if action.name != BUY_BOOSTER:
            raise ValueError("booster policy requires BUY_BOOSTER action")

        family = self._family(action.target)
        variant = self._variant(action.target)
        if family is None:
            return self._hold(
                action,
                family=None,
                variant=variant,
                rationale=(
                    "unrecognized booster family; booster fails closed",
                    "unopened booster contents are not predicted",
                ),
            )

        if family not in self.AUTONOMOUS_SAFE_FAMILIES:
            return self._hold(
                action,
                family=family,
                variant=variant,
                rationale=(
                    f"{family} pack post-open targeting is not autonomous-safe yet",
                    "unopened booster contents are not predicted",
                ),
            )

        free_joker_slots = max(0, state.joker_slots - len(state.jokers))
        if family == "BUFFOON" and free_joker_slots <= 0:
            return self._hold(
                action,
                family=family,
                variant=variant,
                rationale=(
                    "Buffoon pack requires a free Joker slot in the current pack policy",
                    "replacement from an opened pack is not executable yet",
                    "unopened booster contents are not predicted",
                ),
            )

        price = self.shop_policy._price(action.target)
        if price > state.money:
            return self._hold(
                action,
                family=family,
                variant=variant,
                rationale=(
                    f"booster costs ${price} but only ${state.money} is available",
                    "unopened booster contents are not predicted",
                ),
            )

        option_utility, build_notes = self._option_utility(
            state,
            family=family,
            variant=variant,
            free_joker_slots=free_joker_slots,
        )
        remaining = state.money - price
        price_penalty = price * self.shop_policy.price_weight
        interest_penalty = (
            self.shop_policy._interest(state.money)
            - self.shop_policy._interest(remaining)
        ) * self.shop_policy.interest_weight
        reserve_penalty = self.shop_policy._incremental_reserve_shortfall(
            state.money,
            remaining,
        ) * self.shop_policy.reserve_weight
        total = (
            option_utility
            - price_penalty
            - interest_penalty
            - reserve_penalty
        )
        required = self.shop_policy.hold_bias + self.thresholds.minimum_margin
        rationale = (
            f"booster family={family} variant={variant}",
            *build_notes,
            f"option utility={option_utility:.3f}",
            f"price penalty={price_penalty:.3f}",
            f"interest penalty={interest_penalty:.3f}",
            f"reserve penalty={reserve_penalty:.3f}",
            f"booster score={total:.3f}; required>{required:.3f}",
            "unopened booster contents are not predicted",
        )

        return ShopBoosterRecommendation(
            decision="BUY" if total > required else "HOLD",
            action=action,
            family=family,
            variant=variant,
            total=total,
            option_utility=option_utility,
            price_penalty=price_penalty,
            interest_penalty=interest_penalty,
            reserve_penalty=reserve_penalty,
            rationale=rationale,
        )

    def _option_utility(
        self,
        state: BalatroState,
        *,
        family: str,
        variant: str,
        free_joker_slots: int,
    ) -> tuple[float, tuple[str, ...]]:
        if family == "CELESTIAL":
            profile = self.build_profiler.profile(state)
            investment = max(
                (max(0, int(level) - 1) for _, level in profile.hand_levels),
                default=0,
            )
            build_bonus = min(
                self.thresholds.max_hand_investment_bonus,
                investment * self.thresholds.hand_investment_weight,
            )
            base = self.thresholds.celestial_base
            notes = (
                f"maximum hand-level investment={investment}",
                f"hand specialization bonus={build_bonus:.3f}",
            )
        elif family == "BUFFOON":
            build_bonus = min(
                self.thresholds.max_free_joker_slot_bonus,
                free_joker_slots * self.thresholds.free_joker_slot_bonus,
            )
            base = self.thresholds.buffoon_base
            notes = (
                f"free Joker slots={free_joker_slots}",
                f"Joker-slot option bonus={build_bonus:.3f}",
            )
        else:
            base = self.thresholds.standard_base
            build_bonus = 0.0
            notes = ("Standard pack receives conservative generic deck option value",)

        variant_bonus = 0.0
        if variant == "JUMBO":
            variant_bonus = self.thresholds.jumbo_bonus
        elif variant == "MEGA":
            variant_bonus = self.thresholds.mega_bonus

        return base + build_bonus + variant_bonus, (
            *notes,
            f"visible pack-size option bonus={variant_bonus:.3f}",
        )

    @staticmethod
    def _text(item) -> str:
        values = (
            getattr(item, "label", ""),
            getattr(item, "center", ""),
            getattr(item, "kind", ""),
        )
        return " ".join(str(value).upper() for value in values if value)

    @classmethod
    def _family(cls, item) -> str | None:
        text = cls._text(item)
        for family in ("CELESTIAL", "BUFFOON", "STANDARD", "ARCANA", "SPECTRAL"):
            if family in text:
                return family
        return None

    @classmethod
    def _variant(cls, item) -> str:
        text = cls._text(item)
        if "MEGA" in text:
            return "MEGA"
        if "JUMBO" in text:
            return "JUMBO"
        return "NORMAL"

    @staticmethod
    def _hold(
        action: BalatroAction,
        *,
        family: str | None,
        variant: str | None,
        rationale: tuple[str, ...],
    ) -> ShopBoosterRecommendation:
        return ShopBoosterRecommendation(
            decision="HOLD",
            action=action,
            family=family,
            variant=variant,
            total=float("-inf"),
            rationale=rationale,
        )
