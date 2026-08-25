from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Mapping

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND
from games.balatro.build.effects import SCORE_CHIPS, SCORE_MULT, SCORE_XMULT
from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BuildProfile,
)


DEFAULT_BLIND_SKIP_THRESHOLD = 2.0
DEFAULT_FALLBACK_TAG_VALUE = 4.0

# Baseline public utility for normal skip tags. These are policy-scale values,
# not cash-equivalent claims. State-dependent tags are refined below.
CONSERVATIVE_TAG_VALUES = {
    "tag_uncommon": 5.0,
    "tag_rare": 7.0,
    "tag_negative": 9.0,
    "tag_foil": 5.0,
    "tag_holo": 5.5,
    "tag_polychrome": 7.0,
    "tag_investment": 25.0,
    "tag_voucher": 5.0,
    "tag_boss": 2.0,
    "tag_standard": 5.0,
    "tag_charm": 6.0,
    "tag_meteor": 6.0,
    "tag_buffoon": 6.0,
    "tag_handy": 4.0,
    "tag_garbage": 4.0,
    "tag_ethereal": 6.0,
    "tag_coupon": 7.0,
    "tag_double": 4.0,
    "tag_juggle": 4.0,
    "tag_d_six": 4.0,
    "tag_top_up": 5.0,
    "tag_skip": 5.0,
    "tag_orbital": 6.0,
    "tag_economy": 0.0,
}

_SCORING_FEATURES = frozenset({SCORE_CHIPS, SCORE_MULT, SCORE_XMULT})
_JOKER_DEVELOPMENT_TAGS = frozenset(
    {
        "tag_uncommon",
        "tag_rare",
        "tag_foil",
        "tag_holo",
        "tag_polychrome",
        "tag_buffoon",
    }
)
_CONSUMABLE_DEVELOPMENT_TAGS = frozenset({"tag_charm", "tag_ethereal"})
_HAND_DEVELOPMENT_TAGS = frozenset({"tag_meteor", "tag_orbital"})


@dataclass(frozen=True)
class BlindSkipThresholds:
    """D13-only play-vs-skip controls for the active playbook."""

    minimum_skip_advantage: float = DEFAULT_BLIND_SKIP_THRESHOLD
    fallback_tag_value: float = DEFAULT_FALLBACK_TAG_VALUE
    base_shop_opportunity_value: float = 1.5
    build_development_shop_weight: float = 2.0
    free_joker_slot_shop_weight: float = 0.4
    cash_recovery_shop_weight: float = 0.25
    late_ante_shop_weight: float = 0.2
    pre_boss_shop_weight: float = 2.5
    interest_cap: int = 5
    tag_build_fit_weight: float = 2.0
    max_tag_build_adjustment: float = 2.5

    def __post_init__(self) -> None:
        for name in (
            "minimum_skip_advantage",
            "fallback_tag_value",
            "base_shop_opportunity_value",
            "build_development_shop_weight",
            "free_joker_slot_shop_weight",
            "cash_recovery_shop_weight",
            "late_ante_shop_weight",
            "pre_boss_shop_weight",
            "tag_build_fit_weight",
            "max_tag_build_adjustment",
        ):
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.interest_cap) < 0:
            raise ValueError("interest_cap cannot be negative")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "BlindSkipThresholds":
        if not value:
            return cls()
        allowed = {item.name for item in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D13 blind-skip threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})


@dataclass(frozen=True)
class BlindSkipDecision:
    action_name: str
    blind_type: str
    play_ev: float
    blind_reward_ev: float
    blind_reward_source: str
    interest_opportunity_cost: float
    shop_opportunity_cost: float
    boss_preparation_cost: float
    tag_ev: float
    tag_build_adjustment: float
    skip_ev: float
    margin: float
    threshold: float
    build_readiness: float
    tag_value_source: str
    tag_key: str | None = None

    @property
    def economy_opportunity_cost(self) -> float:
        # Preserve the v0.9 snapshot-only compatibility contract. Contextual v1.0
        # decisions expose blind reward and interest separately, while the legacy
        # entry point historically used this name for only its cash-poor penalty.
        if self.blind_reward_source == "legacy_play_ev_proxy":
            return self.interest_opportunity_cost
        return self.blind_reward_ev + self.interest_opportunity_cost

    @property
    def notes(self) -> tuple[str, ...]:
        decision = "SKIP" if self.action_name == SKIP_BLIND else "PLAY"
        return (
            f"blind_decision={decision}",
            f"blind_type={self.blind_type}",
            f"tag_key={self.tag_key or 'NONE'}",
            f"build_readiness={self.build_readiness:.3f}",
            f"blind_reward_ev={self.blind_reward_ev:.3f}",
            f"blind_reward_source={self.blind_reward_source}",
            f"interest_opportunity_cost={self.interest_opportunity_cost:.3f}",
            f"shop_opportunity_cost={self.shop_opportunity_cost:.3f}",
            f"boss_preparation_cost={self.boss_preparation_cost:.3f}",
            f"play_ev={self.play_ev:.3f}",
            f"tag_ev={self.tag_ev:.3f}",
            f"tag_build_adjustment={self.tag_build_adjustment:.3f}",
            f"tag_value_source={self.tag_value_source}",
            f"skip_ev={self.skip_ev:.3f}",
            f"skip_margin={self.margin:.3f}",
            f"skip_threshold={self.threshold:.3f}",
        )


def _number(value, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return float(default)
    return float(value)


def _tag_key(value) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _joker_open_slots(payload: dict, state) -> int | None:
    if state is not None:
        limit = getattr(state, "joker_slots", None)
        jokers = getattr(state, "jokers", None)
        if isinstance(limit, int) and jokers is not None:
            return max(0, int(limit) - len(jokers))

    jokers = payload.get("jokers")
    if not isinstance(jokers, dict):
        return None
    count = jokers.get("count")
    limit = jokers.get("limit")
    if isinstance(count, bool) or not isinstance(count, (int, float)):
        return None
    if isinstance(limit, bool) or not isinstance(limit, (int, float)):
        return None
    return max(0, int(limit) - int(count))


def _observed_tag_value(tag_key: str, payload: dict, state) -> float | None:
    if tag_key not in CONSERVATIVE_TAG_VALUES:
        return None

    money = int(getattr(state, "money", _number(payload.get("money"), 0.0)))

    if tag_key == "tag_economy":
        return min(40.0, max(0.0, float(money)))

    if tag_key == "tag_top_up":
        open_slots = _joker_open_slots(payload, state)
        if open_slots is not None:
            return min(2, open_slots) * 2.5

    if tag_key == "tag_handy" and state is not None:
        played = getattr(state, "hand_play_counts", None)
        if isinstance(played, dict):
            return max(
                float(CONSERVATIVE_TAG_VALUES[tag_key]),
                float(sum(max(0, int(value)) for value in played.values())),
            )

    return float(CONSERVATIVE_TAG_VALUES[tag_key])


def _blind_reward_value(blind_type: str, payload: dict, state) -> tuple[float, str]:
    blind = payload.get("blind")
    blind = blind if isinstance(blind, dict) else {}
    observed = blind.get("reward")
    if (
        not isinstance(observed, bool)
        and isinstance(observed, (int, float))
        and float(observed) > 0.0
    ):
        return float(observed), "observed_live_blind_reward"

    live_blind = getattr(state, "blind", None)
    translated = getattr(live_blind, "reward", None)
    if (
        not isinstance(translated, bool)
        and isinstance(translated, (int, float))
        and float(translated) > 0.0
    ):
        return float(translated), "translated_live_blind_reward"

    # White Stake fallback. Later stake milestones own stake-specific reward changes.
    return (
        {
            "SMALL": 3.0,
            "BIG": 4.0,
            "BOSS": 5.0,
        }.get(blind_type, 5.0),
        "red_white_blind_reward_fallback",
    )


def _build_readiness(profile: BuildProfile) -> float:
    joker_capacity = max(1, int(profile.joker_slots))
    occupied_jokers = max(0, joker_capacity - int(profile.free_joker_slots))
    joker_fill = min(1.0, occupied_jokers / joker_capacity)
    hand_investment = min(
        1.0,
        sum(max(0.0, float(level) - 1.0) for _, level in profile.hand_levels) / 6.0,
    )
    scoring_features = sum(
        1 for feature in _SCORING_FEATURES if profile.strength(feature) > 0.0
    )
    scoring_readiness = min(1.0, scoring_features / 3.0)
    return max(
        0.0,
        min(
            1.0,
            0.40 * joker_fill
            + 0.30 * hand_investment
            + 0.30 * scoring_readiness,
        ),
    )


def _tag_build_adjustment(
    tag_key: str | None,
    profile: BuildProfile,
    readiness: float,
    thresholds: BlindSkipThresholds,
) -> float:
    if tag_key is None:
        return 0.0

    need = max(0.0, 1.0 - readiness)
    open_joker_ratio = min(1.0, max(0, profile.free_joker_slots) / 2.0)
    free_consumable_ratio = min(
        1.0,
        max(0, profile.free_consumable_slots) / max(1, profile.consumable_slots),
    )
    hand_investment = min(
        1.0,
        sum(max(0.0, float(level) - 1.0) for _, level in profile.hand_levels) / 4.0,
    )
    if tag_key == "tag_negative":
        fit = 0.5 + 0.5 * need
    elif tag_key in _JOKER_DEVELOPMENT_TAGS:
        fit = 0.65 * need + 0.35 * open_joker_ratio
    elif tag_key in _CONSUMABLE_DEVELOPMENT_TAGS:
        fit = 0.60 * free_consumable_ratio + 0.40 * need
    elif tag_key in _HAND_DEVELOPMENT_TAGS:
        fit = max(hand_investment, need)
    elif tag_key == "tag_voucher":
        fit = min(1.0, max(0.0, (8.0 - float(profile.ante)) / 7.0))
    elif tag_key == "tag_standard":
        fit = need
    else:
        fit = 0.0

    return min(
        float(thresholds.max_tag_build_adjustment),
        max(0.0, fit * float(thresholds.tag_build_fit_weight)),
    )


def _shop_opportunity_cost(
    profile: BuildProfile,
    readiness: float,
    thresholds: BlindSkipThresholds,
) -> float:
    free_slot_value = min(2, max(0, int(profile.free_joker_slots))) * float(
        thresholds.free_joker_slot_shop_weight
    )
    cash_recovery = min(
        2.0,
        max(0.0, 5.0 - float(profile.money))
        * float(thresholds.cash_recovery_shop_weight),
    )
    late_ante = min(5, max(0, int(profile.ante) - 3)) * float(
        thresholds.late_ante_shop_weight
    )
    return (
        float(thresholds.base_shop_opportunity_value)
        + max(0.0, 1.0 - readiness)
        * float(thresholds.build_development_shop_weight)
        + free_slot_value
        + cash_recovery
        + late_ante
    )


class BuildAwareBlindSkipPolicy:
    """D13 contextual play-vs-skip policy using public run state only."""

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()

    def decide(
        self,
        snapshot,
        state,
        *,
        thresholds: BlindSkipThresholds | None = None,
    ) -> BlindSkipDecision:
        thresholds = thresholds or BlindSkipThresholds()
        payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
        blind = payload.get("blind")
        blind = blind if isinstance(blind, dict) else {}
        blind_type = str(blind.get("type") or "UNKNOWN").upper()
        tag_key = _tag_key(blind.get("tag"))

        profile = self.profiler.profile(state)
        readiness = _build_readiness(profile)

        reward_ev, reward_source = _blind_reward_value(blind_type, payload, state)
        interest_cost = min(
            int(thresholds.interest_cap),
            max(0, int(profile.money)) // 5,
        )
        shop_cost = _shop_opportunity_cost(profile, readiness, thresholds)
        boss_cost = (
            float(thresholds.pre_boss_shop_weight) * (1.0 - 0.5 * readiness)
            if blind_type == "BIG"
            else 0.0
        )

        observed_value = (
            _observed_tag_value(tag_key, payload, state)
            if tag_key is not None
            else None
        )
        if observed_value is not None:
            tag_ev = max(0.0, observed_value)
            tag_value_source = f"observed_live_tag:{tag_key}"
        else:
            tag_ev = max(0.0, float(thresholds.fallback_tag_value))
            tag_value_source = (
                f"fallback_unmodeled_live_tag:{tag_key}"
                if tag_key is not None
                else "fallback_unidentified_live_tag"
            )

        tag_adjustment = _tag_build_adjustment(
            tag_key,
            profile,
            readiness,
            thresholds,
        )
        play_ev = reward_ev + float(interest_cost) + shop_cost + boss_cost
        skip_ev = tag_ev + tag_adjustment
        margin = skip_ev - play_ev
        action_name = (
            SKIP_BLIND
            if blind_type in {"SMALL", "BIG"}
            and margin >= float(thresholds.minimum_skip_advantage)
            else SELECT_BLIND
        )

        return BlindSkipDecision(
            action_name=action_name,
            blind_type=blind_type,
            play_ev=play_ev,
            blind_reward_ev=reward_ev,
            blind_reward_source=reward_source,
            interest_opportunity_cost=float(interest_cost),
            shop_opportunity_cost=shop_cost,
            boss_preparation_cost=boss_cost,
            tag_ev=tag_ev,
            tag_build_adjustment=tag_adjustment,
            skip_ev=skip_ev,
            margin=margin,
            threshold=float(thresholds.minimum_skip_advantage),
            build_readiness=readiness,
            tag_value_source=tag_value_source,
            tag_key=tag_key,
        )


def decide_blind_play_or_skip(
    snapshot,
    *,
    state=None,
    threshold: float = DEFAULT_BLIND_SKIP_THRESHOLD,
    fallback_tag_value: float = DEFAULT_FALLBACK_TAG_VALUE,
    thresholds: BlindSkipThresholds | None = None,
    profiler: BalatroBuildProfiler | None = None,
) -> BlindSkipDecision:
    """Compatibility entry point for D13.

    Live callers should provide translated public state. Snapshot-only callers keep
    the conservative v0.9 score path until they migrate.
    """
    if state is None:
        payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
        blind = payload.get("blind")
        blind = blind if isinstance(blind, dict) else {}
        blind_type = str(blind.get("type") or "UNKNOWN").upper()
        tag_key = _tag_key(blind.get("tag"))
        play_ev = {
            "SMALL": 3.0,
            "BIG": 4.0,
            "BOSS": 6.0,
        }.get(blind_type, 6.0)
        money = _number(payload.get("money"), 0.0)
        economy_cost = min(2.0, max(0.0, 5.0 - money) * 0.25)
        observed_value = (
            _observed_tag_value(tag_key, payload, None)
            if tag_key is not None
            else None
        )
        tag_ev = (
            max(0.0, observed_value)
            if observed_value is not None
            else max(0.0, float(fallback_tag_value))
        )
        tag_source = (
            f"observed_live_tag:{tag_key}"
            if observed_value is not None
            else (
                f"fallback_unmodeled_live_tag:{tag_key}"
                if tag_key is not None
                else "fallback_unidentified_live_tag"
            )
        )
        skip_ev = tag_ev - economy_cost
        margin = skip_ev - play_ev
        normalized_threshold = max(0.0, float(threshold))
        return BlindSkipDecision(
            action_name=(
                SKIP_BLIND
                if blind_type in {"SMALL", "BIG"} and margin >= normalized_threshold
                else SELECT_BLIND
            ),
            blind_type=blind_type,
            play_ev=play_ev,
            blind_reward_ev=play_ev,
            blind_reward_source="legacy_play_ev_proxy",
            interest_opportunity_cost=economy_cost,
            shop_opportunity_cost=0.0,
            boss_preparation_cost=0.0,
            tag_ev=tag_ev,
            tag_build_adjustment=0.0,
            skip_ev=skip_ev,
            margin=margin,
            threshold=normalized_threshold,
            build_readiness=0.0,
            tag_value_source=tag_source,
            tag_key=tag_key,
        )

    configured = thresholds or BlindSkipThresholds()
    configured = replace(
        configured,
        minimum_skip_advantage=max(0.0, float(threshold)),
        fallback_tag_value=max(0.0, float(fallback_tag_value)),
    )
    return BuildAwareBlindSkipPolicy(
        profiler=profiler,
    ).decide(snapshot, state, thresholds=configured)
