from __future__ import annotations

"""Safety-first Balatro policy calibrated from the 2026-08-19 five-run batch.

This layer deliberately separates *build coherence* from *can the run survive the
next blind?*.  The live logs showed that deep engineered-clear search could erase
a good discard recommendation, play below required pace, and spend tens of seconds
on a decision even though the basic survival invariant was simple.

The policy therefore owns seven narrow corrections:

* current-hand pace is authoritative over multi-step engineered clear paths;
* when no current hand reaches pace and a discard exists, discard instead of
  burning a hand below pace;
* live adaptive search is advisory and shallow rather than a deep authoritative
  hand-play planner;
* Hologram is Silver alone and only becomes Gold with a repeatable card generator;
* generic pack spending is suppressed while independent scoring readiness is low;
* undeveloped builds may not skip blinds merely because a tag has large nominal EV;
* scoring readiness is computed independently from universal strategy score.
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
from games.balatro.strategy import AVAILABLE
from games.balatro.strategy_booster_policy import StrategyAwareShopBoosterPolicy
from games.balatro.strategy_conditional_relationships import StateAwareBalatroStrategyTracker


_HOLOGRAM_GENERATORS = frozenset({"marblejoker", "certificatejoker", "dnajoker"})


def _token(item: object) -> str:
    value = getattr(item, "name", None) or getattr(item, "label", None) or type(item).__name__
    token = "".join(ch for ch in str(value).lower() if ch.isalnum())
    if token and not token.endswith("joker"):
        token = f"{token}joker"
    return token


def _owned_tokens(state) -> frozenset[str]:
    return frozenset(_token(joker) for joker in (getattr(state, "jokers", ()) or ()))


def _hologram_has_generator(state) -> bool:
    return bool(_owned_tokens(state) & _HOLOGRAM_GENERATORS)


def _scoring_readiness(state) -> float:
    """Return scoring readiness independent from strategy-coherence score.

    This intentionally ignores strategy score and Joker-slot fill.  A full board
    with no chips/mult/xmult and no leveled hand is still weak.  Conversely, a
    compact board with real scoring effects can be ready.
    """
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
    # XMult is the strongest qualitative readiness signal; give it a small bump.
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

    # D1: eliminate authoritative multi-step engineered-clear play.  Search may
    # suggest which discard is attractive, but the actual play invariant is local
    # and deterministic: clear now, meet pace now, or discard to improve the hand.
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

        # Only a current-hand deterministic clear bypasses the pace rule.  A
        # multi-action expectimax line is never an authoritative PLAY decision.
        immediate_clears = [
            plan
            for plan in plays
            if scores[id(plan)] + self.EPSILON >= remaining_blind
            and float(getattr(projections[id(plan)], "clear_probability", 0.0)) >= 1.0 - self.EPSILON
        ]
        if immediate_clears:
            selected = max(immediate_clears, key=lambda plan: scores[id(plan)])
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
            # The survival rule is satisfied; use the highest projected current
            # score rather than preserving hands for a speculative future line.
            selected = max(pace_plays, key=lambda plan: scores[id(plan)])
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
                    "safe-pace policy: play the strongest current hand that meets remaining-score / hands-left pace",
                    "strategy shaping cannot justify an under-pace play",
                ),
                plans=plans,
                search_attempts=search_attempts,
            )

        if discards and int(getattr(state, "discards_remaining", 0) or 0) > 0:
            # Never burn a hand below pace while a legal discard can search for a
            # better scoring hand.  Search/evaluator value only chooses *which*
            # discard; it no longer decides whether to waste the scoring hand.
            selected = max(
                discards,
                key=lambda plan: (
                    float(self.evaluator.evaluate(state, plan.action)),
                    self._within_type_key(plan),
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
                ),
                plans=plans,
                search_attempts=search_attempts,
            )

        # No discard remains: now and only now is an under-pace play unavoidable.
        selected = best_immediate
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
                "play the highest projected immediate score as the forced recovery action",
            ),
            plans=plans,
            search_attempts=search_attempts,
        )

    LiveHandActionPolicy.decide = decide

    # Hologram: owning Hologram alone is support, not a complete Gold engine.
    original_assess = StateAwareBalatroStrategyTracker.assess

    def assess(self, state):
        assessments = tuple(original_assess(self, state))
        if _hologram_has_generator(state):
            return assessments
        adjusted = []
        for assessment in assessments:
            if assessment.strategy_id != "hologram_growth":
                adjusted.append(assessment)
                continue
            score = min(float(assessment.score), 3.0)
            base_score = min(float(getattr(assessment, "base_score", score)), 3.0)
            status = assessment.status if score > 0.0 else AVAILABLE
            adjusted.append(
                replace(
                    assessment,
                    score=score,
                    base_score=base_score,
                    status=status,
                    rationale=(
                        *assessment.rationale,
                        "Hologram is Silver alone; Gold requires Marble Joker, Certificate, or DNA to repeatedly add playing cards",
                    ),
                )
            )
        return tuple(sorted(adjusted, key=lambda item: (-float(item.score), item.strategy_id)))

    StateAwareBalatroStrategyTracker.assess = assess

    # Independent scoring-readiness gate for generic booster spending.
    original_booster_recommend = StrategyAwareShopBoosterPolicy.recommend

    def booster_recommend(self, state, action):
        recommendation = original_booster_recommend(self, state, action)
        family = str(getattr(recommendation, "family", "")).upper()
        if family in {"BUFFOON", "SPECTRAL"}:
            return recommendation
        readiness = _scoring_readiness(state)
        if readiness >= 0.40:
            return recommendation
        # A weak build should spend on visible scoring Jokers/rerolls first.  Keep
        # generic packs possible only when their modeled advantage is exceptional.
        advantage = float(getattr(recommendation, "advantage_over_save", 0.0))
        if advantage >= 2.5:
            return recommendation
        decision = getattr(recommendation, "decision", None)
        hold_value = "HOLD" if isinstance(decision, str) else decision
        return replace(
            recommendation,
            decision=hold_value,
            rationale=(
                *recommendation.rationale,
                f"scoring-readiness gate={readiness:.3f} < 0.400",
                "generic pack deferred until the build has enough real scoring capacity; Joker development/rerolls take priority",
            ),
        )

    StrategyAwareShopBoosterPolicy.recommend = booster_recommend

    # Survival gate for D13.  Large nominal tag EV cannot skip a blind when the
    # build still lacks real scoring capacity.
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

    # Reduce deep-search authority/cost in the module that owns live D1 deepening.
    # This keeps the public helper unchanged for offline diagnostics/tests while the
    # live hand-action engine receives a single bounded advisory pass.
    import games.balatro.live.hand_action_policy as hand_action_module

    hand_action_module.adaptive_blind_search_schedule = _safe_search_schedule
    LiveHandActionPolicy._safe_pace_optimization_installed = True
