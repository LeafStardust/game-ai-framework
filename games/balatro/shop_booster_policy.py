from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.build import BalatroBuildProfiler
from games.balatro.state import BalatroState


BUY = "BUY"
HOLD = "HOLD"
SAVE = HOLD


@dataclass(frozen=True)
class BoosterAcquisitionThresholds:
    """Thresholds owned only by D8 Balatro booster-acquisition decisions.

    Family probabilities are conservative per-visible-offer priors for an unopened
    in-game pack. They do not predict the hidden identities in a particular pack.
    D8 combines those priors with public BuildProfile needs, visible pack size, run
    stage, and in-game transaction economics against a SAVE/HOLD baseline of zero.
    """

    minimum_buy_advantage: float = 0.35
    minimum_pack_hit_probability: float = 0.45
    price_weight: float = 0.35
    interest_weight: float = 1.25
    reserve_target: int = 5
    reserve_weight: float = 0.45

    celestial_per_offer_hit_probability: float = 0.40
    buffoon_per_offer_hit_probability: float = 0.42
    standard_per_offer_hit_probability: float = 0.32
    arcana_per_offer_hit_probability: float = 0.30
    spectral_per_offer_hit_probability: float = 0.22

    celestial_hit_value: float = 4.5
    buffoon_hit_value: float = 5.0
    standard_hit_value: float = 4.0
    arcana_hit_value: float = 4.2
    spectral_hit_value: float = 5.0

    need_hit_probability_bonus: float = 0.25
    need_value_weight: float = 2.0
    runway_value_weight: float = 0.75
    second_selection_value_fraction: float = 0.55

    def __post_init__(self) -> None:
        nonnegative = (
            "minimum_buy_advantage",
            "price_weight",
            "interest_weight",
            "reserve_weight",
            "celestial_hit_value",
            "buffoon_hit_value",
            "standard_hit_value",
            "arcana_hit_value",
            "spectral_hit_value",
            "need_hit_probability_bonus",
            "need_value_weight",
            "runway_value_weight",
            "second_selection_value_fraction",
        )
        for name in nonnegative:
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.reserve_target) < 0:
            raise ValueError("reserve_target cannot be negative")

        probabilities = (
            "minimum_pack_hit_probability",
            "celestial_per_offer_hit_probability",
            "buffoon_per_offer_hit_probability",
            "standard_per_offer_hit_probability",
            "arcana_per_offer_hit_probability",
            "spectral_per_offer_hit_probability",
        )
        for name in probabilities:
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "BoosterAcquisitionThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D8 booster threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


# Compatibility name retained for callers from the earlier B5 scaffold.
ShopBoosterThresholds = BoosterAcquisitionThresholds


@dataclass(frozen=True)
class ShopBoosterRecommendation:
    decision: str
    action: BalatroAction
    family: str | None
    variant: str | None
    total: float
    advantage_over_save: float = 0.0
    option_utility: float = 0.0
    build_need_score: float = 0.0
    per_offer_hit_probability: float = 0.0
    at_least_one_hit_probability: float = 0.0
    offer_count: int = 0
    selection_count: int = 0
    runway_factor: float = 0.0
    price_penalty: float = 0.0
    interest_penalty: float = 0.0
    reserve_penalty: float = 0.0
    rationale: tuple[str, ...] = ()

    @property
    def should_buy(self) -> bool:
        return self.decision == BUY


class BuildAwareShopBoosterPolicy:
    """D8 BUY-versus-SAVE policy for unopened Balatro in-game packs.

    Hidden pack identities are never inspected. D8 estimates only the public
    opportunity represented by pack family, BuildProfile, pack size, run stage,
    and observed in-game price. D9 owns visible offer choice/Skip after opening;
    D10 owns any follow-up effect target.
    """

    AUTONOMOUS_SAFE_FAMILIES = frozenset({"CELESTIAL", "BUFFOON", "STANDARD"})

    PACK_LAYOUTS = {
        "STANDARD": {"NORMAL": (3, 1), "JUMBO": (5, 1), "MEGA": (5, 2)},
        "ARCANA": {"NORMAL": (3, 1), "JUMBO": (5, 1), "MEGA": (5, 2)},
        "CELESTIAL": {"NORMAL": (3, 1), "JUMBO": (5, 1), "MEGA": (5, 2)},
        "BUFFOON": {"NORMAL": (2, 1), "JUMBO": (4, 1), "MEGA": (4, 2)},
        "SPECTRAL": {"NORMAL": (2, 1), "JUMBO": (4, 1), "MEGA": (4, 2)},
    }

    FAMILY_CARD_FEATURE_PREFIXES = {
        "STANDARD": (
            "rank:",
            "suit:",
            "enhancement:",
            "seal:",
            "edition:",
            "held:",
        ),
        "ARCANA": ("rank:", "suit:", "enhancement:", "held:"),
        "SPECTRAL": (
            "rank:",
            "suit:",
            "enhancement:",
            "seal:",
            "edition:",
            "held:",
        ),
    }
    FAMILY_TRANSFORM_FEATURES = {
        "STANDARD": frozenset({"target:card"}),
        "ARCANA": frozenset({"deck:transform", "deck:remove", "target:card"}),
        "SPECTRAL": frozenset({"deck:transform", "deck:remove", "target:card"}),
    }

    def __init__(
        self,
        *,
        build_profiler: BalatroBuildProfiler | None = None,
        thresholds: BoosterAcquisitionThresholds | None = None,
        shop_policy=None,
    ) -> None:
        # D12 still expects child totals on its historical absolute shop-score
        # scale. This baseline is representation-only: D8 admission is decided
        # entirely from advantage_over_save and D8-owned thresholds below.
        self.parent_hold_baseline = float(
            getattr(shop_policy, "hold_bias", 0.35)
        ) if shop_policy is not None else 0.35
        self.build_profiler = build_profiler or BalatroBuildProfiler()
        self.thresholds = thresholds or BoosterAcquisitionThresholds()

    def recommend(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> ShopBoosterRecommendation:
        if state.phase != "SHOP":
            raise ValueError("D8 booster acquisition requires SHOP phase")
        if action.name != BUY_BOOSTER:
            raise ValueError("D8 booster acquisition requires BUY_BOOSTER action")

        family = self._family(action.target)
        variant = self._variant(action.target)
        if family is None:
            return self._hold(
                action,
                family=None,
                variant=variant,
                rationale=(
                    "unrecognized booster family; SAVE/HOLD fails closed",
                    "unopened booster contents are not predicted",
                ),
            )

        price = self._price(action.target)
        if price > int(state.money):
            return self._hold(
                action,
                family=family,
                variant=variant,
                rationale=(
                    f"booster costs ${price} but only ${state.money} is available",
                    "unopened booster contents are not predicted",
                ),
            )

        profile = self.build_profiler.profile(state)
        build_need_score, build_notes = self._build_need(
            state,
            profile,
            family=family,
        )
        offer_count, selection_count = self.PACK_LAYOUTS[family][variant]
        runway_factor = self._runway_factor(profile.ante)
        per_offer_probability = self._clamp_probability(
            self._base_hit_probability(family)
            + build_need_score * self.thresholds.need_hit_probability_bonus
        )

        if family == "BUFFOON" and profile.free_joker_slots <= 0:
            per_offer_probability = 0.0
            build_notes = (
                *build_notes,
                "no free Joker slot; opened-pack Joker replacement is not admitted",
            )

        at_least_one = 1.0 - (1.0 - per_offer_probability) ** offer_count
        hit_value = (
            self._base_hit_value(family)
            + build_need_score * self.thresholds.need_value_weight
            + runway_factor * self.thresholds.runway_value_weight
        )
        selection_multiplier = 1.0 + max(0, selection_count - 1) * (
            self.thresholds.second_selection_value_fraction
        )
        option_utility = at_least_one * hit_value * selection_multiplier

        remaining = int(state.money) - price
        price_penalty = price * self.thresholds.price_weight
        interest_penalty = (
            self._interest(int(state.money)) - self._interest(remaining)
        ) * self.thresholds.interest_weight
        reserve_penalty = self._incremental_reserve_shortfall(
            int(state.money),
            remaining,
        ) * self.thresholds.reserve_weight
        advantage = option_utility - price_penalty - interest_penalty - reserve_penalty
        total = self.parent_hold_baseline + advantage

        probability_ok = (
            at_least_one >= self.thresholds.minimum_pack_hit_probability
        )
        advantage_ok = advantage > self.thresholds.minimum_buy_advantage
        autonomy_safe = family in self.AUTONOMOUS_SAFE_FAMILIES
        decision = BUY if probability_ok and advantage_ok and autonomy_safe else HOLD
        rationale = (
            f"booster family={family} variant={variant}",
            *build_notes,
            f"visible pack layout offers={offer_count} selections={selection_count}",
            f"build need score={build_need_score:.3f}",
            f"per-offer useful-choice prior={per_offer_probability:.3f}",
            f"P(at least one useful visible offer)={at_least_one:.3f}",
            f"runway factor={runway_factor:.3f}",
            f"option EV={option_utility:.3f}",
            f"price penalty={price_penalty:.3f}",
            f"interest penalty={interest_penalty:.3f}",
            f"reserve penalty={reserve_penalty:.3f}",
            f"D8 advantage over SAVE=0 is {advantage:.3f}; "
            f"required>{self.thresholds.minimum_buy_advantage:.3f}",
            f"hit-probability threshold="
            f"{self.thresholds.minimum_pack_hit_probability:.3f}",
            (
                "post-open family is autonomous-safe"
                if autonomy_safe
                else f"{family} post-open autonomy remains deferred to D9/D10"
            ),
            "unopened booster contents are not predicted",
        )
        return ShopBoosterRecommendation(
            decision=decision,
            action=action,
            family=family,
            variant=variant,
            total=total,
            advantage_over_save=advantage,
            option_utility=option_utility,
            build_need_score=build_need_score,
            per_offer_hit_probability=per_offer_probability,
            at_least_one_hit_probability=at_least_one,
            offer_count=offer_count,
            selection_count=selection_count,
            runway_factor=runway_factor,
            price_penalty=price_penalty,
            interest_penalty=interest_penalty,
            reserve_penalty=reserve_penalty,
            rationale=rationale,
        )

    def _build_need(
        self,
        state: BalatroState,
        profile,
        *,
        family: str,
    ) -> tuple[float, tuple[str, ...]]:
        if family == "CELESTIAL":
            investment = max(
                (max(0, int(level) - 1) for _, level in profile.hand_levels),
                default=0,
            )
            investment_score = min(1.0, investment / 4.0)
            plays = [
                max(0, int(value))
                for value in (getattr(state, "hand_play_counts", {}) or {}).values()
            ]
            total_plays = sum(plays)
            concentration = (
                max(plays, default=0) / total_plays if total_plays > 0 else 0.0
            )
            need = min(1.0, investment_score * 0.60 + concentration * 0.40)
            return need, (
                f"maximum hand-level investment={investment}",
                f"observed hand-play concentration={concentration:.3f}",
            )

        if family == "BUFFOON":
            denominator = max(1, int(profile.joker_slots))
            need = min(1.0, profile.free_joker_slots / denominator)
            return need, (
                f"free Joker slots={profile.free_joker_slots}/{profile.joker_slots}",
            )

        demanded: set[str] = set()
        for descriptor in profile.effects:
            demanded.update(descriptor.requires)
            demanded.update(descriptor.scales_with)
            demanded.update(descriptor.amplifies)

        prefixes = self.FAMILY_CARD_FEATURE_PREFIXES.get(family, ())
        exact = self.FAMILY_TRANSFORM_FEATURES.get(family, frozenset())
        relevant = {
            feature
            for feature in demanded
            if feature in exact
            or any(feature.startswith(prefix) for prefix in prefixes)
        }
        unmet = {
            feature
            for feature in relevant
            if profile.strength(feature) <= 0.0 and not profile.can_produce(feature)
        }
        gap_score = min(1.0, len(unmet) / 3.0)

        modified_cards = sum(count for _, count in profile.enhancement_counts)
        modified_cards += sum(count for _, count in profile.seal_counts)
        modified_cards += sum(count for _, count in profile.edition_counts)
        modified_density = (
            min(1.0, modified_cards / max(1, profile.deck_size) / 0.20)
            if profile.deck_size > 0
            else 0.0
        )

        need = (
            min(1.0, gap_score * 0.75 + modified_density * 0.25)
            if family == "STANDARD"
            else gap_score
        )
        unmet_text = ", ".join(sorted(unmet)) if unmet else "none"
        return need, (
            f"relevant unmet build features={unmet_text}",
            f"playing-card modifier density={modified_density:.3f}",
        )

    def _base_hit_probability(self, family: str) -> float:
        return float(
            getattr(
                self.thresholds,
                f"{family.lower()}_per_offer_hit_probability",
            )
        )

    def _base_hit_value(self, family: str) -> float:
        return float(getattr(self.thresholds, f"{family.lower()}_hit_value"))

    @staticmethod
    def _runway_factor(ante: int) -> float:
        return 1.0 / (1.0 + 0.25 * max(0, int(ante) - 1))

    @staticmethod
    def _clamp_probability(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _interest(money: int) -> int:
        return min(5, max(0, int(money)) // 5)

    def _incremental_reserve_shortfall(self, before: int, after: int) -> int:
        target = int(self.thresholds.reserve_target)
        before_shortfall = max(0, target - int(before))
        after_shortfall = max(0, target - int(after))
        return max(0, after_shortfall - before_shortfall)

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
        for family in (
            "CELESTIAL",
            "BUFFOON",
            "STANDARD",
            "ARCANA",
            "SPECTRAL",
        ):
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
            decision=HOLD,
            action=action,
            family=family,
            variant=variant,
            total=float("-inf"),
            rationale=rationale,
        )
