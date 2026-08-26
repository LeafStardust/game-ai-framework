from __future__ import annotations

"""Safety-first Balatro policy calibrated from repeated Red/White runs.

This layer separates build coherence from immediate blind survival. It owns the
runtime corrections that remain valid under the canonical Bond/composition model:

* current-hand pace is authoritative over multi-step engineered clear paths;
* when no current hand reaches pace and a discard exists, discard instead of
  burning a hand below pace;
* live adaptive search is advisory and shallow rather than authoritative;
* undeveloped builds may not skip blinds merely because a tag has large nominal EV;
* scoring readiness is computed from actual scoring effects, not legacy strategy
  scores or categorical tiers.

Within each already-selected action class, canonical D1 full-blind survival ordering
remains authoritative over immediate score or local recovery heuristics.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, SELECT_BLIND, SKIP_BLIND
from games.balatro.blind_skip_policy import BuildAwareBlindSkipPolicy
from games.balatro.build.effects import SCORE_CHIPS, SCORE_MULT, SCORE_XMULT
from games.balatro.build.profile import BalatroBuildProfiler
from games.balatro.live.adaptive_search import AdaptiveBlindSearchConfig
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    PACE_RECOVERY,
    LiveHandActionPolicy,
)


def _scoring_readiness(state) -> float:
    """Return scoring readiness independently from composition coherence."""
    try:
        profile = BalatroBuildProfiler().profile(state)
    except Exception:
        return 0.0

    feature_presence = sum(
        1
        for feature in (SCORE_CHIPS, SCORE_MULT, SCORE_XMULT)
        if float(profile.strength(feature)) > 0.0
    )
    feature_score = min(1.0, feature_presence / 3.0)
    hand_investment = min(
        1.0,
        sum(max(0.0, float(level) - 1.0) for _, level in profile.hand_levels) / 5.0,
    )
    xmult_bonus = 0.10 if float(profile.strength(SCORE_XMULT)) > 0.0 else 0.0
    return min(1.0, 0.65 * feature_score + 0.35 * hand_investment + xmult_bonus)


def _safe_search_schedule(
    *,
    hands_remaining: int,
    discards_remaining: int,
    max_horizon: int = 8,
    max_nodes: int = 5000,
) -> tuple[AdaptiveBlindSearchConfig, ...]:
    """One shallow advisory pass; never engineer a five-action clear line live."""
    if hands_remaining < 0 or discards_remaining < 0:
        raise ValueError("remaining hands/discards cannot be negative")
    if hands_remaining + discards_remaining <= 0:
        return ()
    if max_horizon < 1 or max_nodes < 1:
        raise ValueError("search horizon/nodes must be positive")

    horizon = 1 if hands_remaining + discards_remaining == 1 else 2
    return (
        AdaptiveBlindSearchConfig(
            horizon=horizon,
            samples=8,
            child_samples=1,
            play_width=3,
            discard_width=2 if discards_remaining > 0 else 0,
            child_play_width=1,
            child_discard_width=1 if discards_remaining > 0 else 0,
            max_nodes=min(int(max_nodes), 750),
        ),
    )


def install_safe_pace_optimization_policy() -> None:
    if getattr(LiveHandActionPolicy, "_safe_pace_optimization_installed", False):
        return

    original_decide = LiveHandActionPolicy.decide

    def decide(
        self,
        state,
        plans,
        *,
        search_attempts=(),
        confirmed_clear_path=None,
        setup_discard_consensus=False,
    ):
        plans = tuple(plans)
        plays = [plan for plan in plans if plan.action.name == PLAY_CARDS]
        discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
        if not plays:
            return original_decide(
                self,
                state,
                plans,
                search_attempts=search_attempts,
                confirmed_clear_path=None,
                setup_discard_consensus=setup_discard_consensus,
            )

        best_play = max(plays, key=self._within_type_key)
        best_discard = max(discards, key=self._within_type_key) if discards else None
        pace_target = self._pace_target(state)
        hands_left = max(1, int(getattr(state, "hands_remaining", 1) or 1))
        remaining_blind = max(0.0, pace_target * hands_left)

        projections = {id(plan): self.evaluator.project_play(state, plan.action) for plan in plays}
        scores = {id(plan): float(projections[id(plan)].expected_hand_score) for plan in plays}
        best_immediate = max(plays, key=lambda plan: scores[id(plan)])
        best_score = scores[id(best_immediate)]
        best_ratio = self._pace_ratio(best_score, pace_target)

        immediate_clears = [
            plan
            for plan in plays
            if scores[id(plan)] + self.EPSILON >= remaining_blind
            and float(getattr(projections[id(plan)], "clear_probability", 0.0)) >= 1.0 - self.EPSILON
        ]
        if immediate_clears:
            selected = max(immediate_clears, key=self._safe_equivalent_clear_key)
            selected_score = scores[id(selected)]
            return self._decision(
                mode=CLEAR_PATH,
                selected=selected,
                best_play=best_play,
                best_discard=best_discard,
                pace_target=pace_target,
                best_play_immediate_score=best_score,
                best_play_pace_ratio=best_ratio,
                selected_immediate_score=selected_score,
                selected_pace_ratio=self._pace_ratio(selected_score, pace_target),
                selected_fallback_value=None,
                clear_path_candidates=len(immediate_clears),
                sampled_clear_path_confirmed=False,
                setup_discard_consensus=False,
                confidence=1.0,
                rationale=(
                    "safe-pace policy: current hand deterministically clears the blind",
                    "among deterministic clears, canonical D1 survival/resource ordering remains authoritative",
                    "multi-step engineered clear paths are advisory only",
                ),
                plans=plans,
                search_attempts=search_attempts,
            )

        pace_plays = [
            plan
            for plan in plays
            if self._pace_ratio(scores[id(plan)], pace_target) + self.EPSILON
            >= self.thresholds.pace_ratio_floor
        ]
        if pace_plays:
            selected = max(
                pace_plays,
                key=lambda plan: self._pace_play_key(
                    plan,
                    self._pace_ratio(scores[id(plan)], pace_target),
                ),
            )
            selected_score = scores[id(selected)]
            selected_ratio = self._pace_ratio(selected_score, pace_target)
            return self._decision(
                mode=PACE_PLAY,
                selected=selected,
                best_play=best_play,
                best_discard=best_discard,
                pace_target=pace_target,
                best_play_immediate_score=best_score,
                best_play_pace_ratio=best_ratio,
                selected_immediate_score=selected_score,
                selected_pace_ratio=selected_ratio,
                selected_fallback_value=None,
                clear_path_candidates=0,
                sampled_clear_path_confirmed=False,
                setup_discard_consensus=False,
                confidence=self._pace_confidence(selected_ratio),
                rationale=(
                    "safe-pace policy: choose among current hands that meet remaining-score / hands-left pace",
                    "canonical D1 full-blind clear probability and plan quality rank pace-qualified plays before local pace closeness",
                    "Bond/composition shaping cannot justify an under-pace play",
                ),
                plans=plans,
                search_attempts=search_attempts,
            )

        if discards and int(getattr(state, "discards_remaining", 0) or 0) > 0:
            selected = max(
                discards,
                key=lambda plan: (
                    *self._within_type_key(plan),
                    float(self.evaluator.evaluate(state, plan.action)),
                ),
            )
            return self._decision(
                mode=PACE_RECOVERY,
                selected=selected,
                best_play=best_play,
                best_discard=best_discard,
                pace_target=pace_target,
                best_play_immediate_score=best_score,
                best_play_pace_ratio=best_ratio,
                selected_immediate_score=None,
                selected_pace_ratio=None,
                selected_fallback_value=float(self.evaluator.evaluate(state, selected.action)),
                clear_path_candidates=0,
                sampled_clear_path_confirmed=False,
                setup_discard_consensus=setup_discard_consensus,
                confidence=0.75 if setup_discard_consensus else 0.60,
                rationale=(
                    "safe-pace policy: no current play meets remaining-score / hands-left pace",
                    "a legal discard remains, so improve the hand instead of burning a scoring hand below pace",
                    "canonical D1 full-blind plan quality ranks discard candidates before local discard heuristic",
                ),
                plans=plans,
                search_attempts=search_attempts,
            )

        selected = max(plays, key=self._within_type_key)
        selected_score = scores[id(selected)]
        selected_ratio = self._pace_ratio(selected_score, pace_target)
        return self._decision(
            mode=PACE_RECOVERY,
            selected=selected,
            best_play=best_play,
            best_discard=None,
            pace_target=pace_target,
            best_play_immediate_score=best_score,
            best_play_pace_ratio=best_ratio,
            selected_immediate_score=selected_score,
            selected_pace_ratio=selected_ratio,
            selected_fallback_value=float(self.evaluator.evaluate(state, selected.action)),
            clear_path_candidates=0,
            sampled_clear_path_confirmed=False,
            setup_discard_consensus=False,
            confidence=0.40,
            rationale=(
                "safe-pace policy: no current play meets pace and no legal discard remains",
                "play the strongest full-blind D1 recovery line; immediate score is secondary to modeled survival/progress",
            ),
            plans=plans,
            search_attempts=search_attempts,
        )

    LiveHandActionPolicy.decide = decide

    original_skip_decide = BuildAwareBlindSkipPolicy.decide

    def blind_skip_decide(self, snapshot, state, *, thresholds=None):
        decision = original_skip_decide(self, snapshot, state, thresholds=thresholds)
        if decision.action_name != SKIP_BLIND:
            return decision
        readiness = _scoring_readiness(state)
        blind_type = str(decision.blind_type).upper()
        required = 0.40 if blind_type == "SMALL" else 0.55
        if readiness >= required:
            return decision
        return replace(
            decision,
            action_name=SELECT_BLIND,
            margin=min(float(decision.margin), -float(decision.threshold)),
            build_readiness=readiness,
            tag_value_source=f"{decision.tag_value_source}; survival-gated",
        )

    BuildAwareBlindSkipPolicy.decide = blind_skip_decide

    import games.balatro.live.hand_action_policy as hand_action_module

    hand_action_module.adaptive_blind_search_schedule = _safe_search_schedule
    LiveHandActionPolicy._safe_pace_optimization_installed = True
