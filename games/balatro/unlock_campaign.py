from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction


HIT_THE_ROAD = "hit_the_road"
STUNTMAN = "stuntman"
AUTO = "auto"


@dataclass(frozen=True)
class JokerUnlockTarget:
    target_id: str
    label: str
    center_key: str


SUPPORTED_JOKER_UNLOCK_TARGETS = {
    HIT_THE_ROAD: JokerUnlockTarget(
        target_id=HIT_THE_ROAD,
        label="Hit the Road",
        center_key="j_hit_the_road",
    ),
    STUNTMAN: JokerUnlockTarget(
        target_id=STUNTMAN,
        label="Stuntman",
        center_key="j_stuntman",
    ),
}


def _normalize_target(value: object) -> str:
    return "_".join(str(value).strip().lower().replace("-", " ").split())


@dataclass(frozen=True)
class UnlockCampaignConfig:
    """Explicit, default-off collection-unlock campaign configuration.

    Normal Red/White competence never receives unlock overrides. ``auto`` expands
    to every currently supported target, after which live public ``unlocked``
    status still gates each handler. Unknown status fails closed.
    """

    targets: tuple[str, ...] = ()

    @classmethod
    def from_targets(cls, values: Iterable[object] | None) -> "UnlockCampaignConfig":
        normalized = tuple(
            dict.fromkeys(
                target
                for value in (values or ())
                if (target := _normalize_target(value))
            )
        )
        if AUTO in normalized:
            normalized = tuple(SUPPORTED_JOKER_UNLOCK_TARGETS)
        unknown = sorted(set(normalized) - set(SUPPORTED_JOKER_UNLOCK_TARGETS))
        if unknown:
            allowed = ", ".join((AUTO, *SUPPORTED_JOKER_UNLOCK_TARGETS))
            raise ValueError(
                "unsupported Joker unlock target(s): "
                + ", ".join(unknown)
                + f"; expected one of {allowed}"
            )
        return cls(normalized)

    @property
    def enabled(self) -> bool:
        return bool(self.targets)


@dataclass(frozen=True)
class UnlockCampaignRecommendation:
    target_id: str
    target_label: str
    action: BalatroAction
    rationale: tuple[str, ...]


class UnlockCampaignPolicy:
    """Rare, target-specific hand override that never lowers clear probability.

    The policy does not modify ordinary strategy, shop, pack, or D1 weights. It
    activates only when explicitly configured and when the authoritative live
    center registry says the target Joker remains locked. Every proposed action is
    compared with the already-selected D1 plan; a lower clear probability is
    rejected.
    """

    STUNTMAN_SCORE = 100_000_000
    EPSILON = 1e-12

    def __init__(
        self,
        config: UnlockCampaignConfig | None = None,
        *,
        preserve_clear_probability: bool = True,
    ) -> None:
        self.config = config or UnlockCampaignConfig()
        self.preserve_clear_probability = bool(preserve_clear_probability)

    def active_targets(self, state) -> tuple[JokerUnlockTarget, ...]:
        if not self.config.enabled:
            return ()
        statuses = getattr(state, "joker_unlocks", None)
        if not isinstance(statuses, dict):
            return ()

        active = []
        for target_id in self.config.targets:
            target = SUPPORTED_JOKER_UNLOCK_TARGETS[target_id]
            status = statuses.get(target.center_key)
            if isinstance(status, dict) and status.get("unlocked") is False:
                active.append(target)
        return tuple(active)

    def recommend_hand(
        self,
        state,
        *,
        baseline_plan,
        evaluate_forced_action: Callable[[BalatroAction], object | None],
        play_actions: Iterable[BalatroAction],
        project_play: Callable[[BalatroAction], object],
    ) -> UnlockCampaignRecommendation | None:
        for target in self.active_targets(state):
            if target.target_id == HIT_THE_ROAD:
                recommendation = self._hit_the_road(
                    state,
                    target,
                    baseline_plan=baseline_plan,
                    evaluate_forced_action=evaluate_forced_action,
                )
            elif target.target_id == STUNTMAN:
                recommendation = self._stuntman(
                    target,
                    baseline_plan=baseline_plan,
                    evaluate_forced_action=evaluate_forced_action,
                    play_actions=play_actions,
                    project_play=project_play,
                )
            else:
                recommendation = None
            if recommendation is not None:
                return recommendation
        return None

    def _hit_the_road(
        self,
        state,
        target: JokerUnlockTarget,
        *,
        baseline_plan,
        evaluate_forced_action: Callable[[BalatroAction], object | None],
    ) -> UnlockCampaignRecommendation | None:
        if int(getattr(state, "discards_remaining", 0)) <= 0:
            return None
        jacks = [
            card
            for card in getattr(state, "hand", ())
            if str(getattr(card, "rank", "")) == "J"
        ]
        if len(jacks) < 5:
            return None

        action = BalatroAction(DISCARD_CARDS, cards=jacks[:5])
        forced = evaluate_forced_action(action)
        if not self._preserves_clear_probability(baseline_plan, forced):
            return None
        return UnlockCampaignRecommendation(
            target_id=target.target_id,
            target_label=target.label,
            action=action,
            rationale=(
                "unlock campaign is explicitly enabled",
                "Hit the Road requirement: discard five Jacks simultaneously",
                "forced discard preserves the selected D1 clear probability",
                f"baseline clear probability={self._clear_probability(baseline_plan):.6f}",
                f"forced clear probability={self._clear_probability(forced):.6f}",
            ),
        )

    def _stuntman(
        self,
        target: JokerUnlockTarget,
        *,
        baseline_plan,
        evaluate_forced_action: Callable[[BalatroAction], object | None],
        play_actions: Iterable[BalatroAction],
        project_play: Callable[[BalatroAction], object],
    ) -> UnlockCampaignRecommendation | None:
        candidates = []
        for action in play_actions:
            if action.name != PLAY_CARDS:
                continue
            projection = project_play(action)
            guaranteed = int(getattr(projection, "hand_score", 0))
            if guaranteed < self.STUNTMAN_SCORE:
                continue
            candidates.append((guaranteed, action))
        candidates.sort(key=lambda item: item[0], reverse=True)

        for guaranteed, action in candidates:
            forced = evaluate_forced_action(action)
            if not self._preserves_clear_probability(baseline_plan, forced):
                continue
            return UnlockCampaignRecommendation(
                target_id=target.target_id,
                target_label=target.label,
                action=action,
                rationale=(
                    "unlock campaign is explicitly enabled",
                    "Stuntman requirement: score at least 100,000,000 in one hand",
                    f"guaranteed modeled hand score={guaranteed}",
                    "forced play preserves the selected D1 clear probability",
                    f"baseline clear probability={self._clear_probability(baseline_plan):.6f}",
                    f"forced clear probability={self._clear_probability(forced):.6f}",
                ),
            )
        return None

    def _preserves_clear_probability(self, baseline_plan, candidate_plan) -> bool:
        if candidate_plan is None:
            return False
        if not self.preserve_clear_probability:
            return True
        return (
            self._clear_probability(candidate_plan) + self.EPSILON
            >= self._clear_probability(baseline_plan)
        )

    @staticmethod
    def _clear_probability(plan) -> float:
        value = getattr(plan, "value", None)
        try:
            return float(getattr(value, "clear_probability", 0.0))
        except (TypeError, ValueError):
            return 0.0
