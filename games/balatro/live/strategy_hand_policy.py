from __future__ import annotations

from collections import Counter
from dataclasses import replace

from games.balatro.aces_dna_hand_policy import _dna_aces_fit
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank, BondRealization
from games.balatro.burnt_bond_execution_policy import _burnt_strategy_fit
from games.balatro.castle_discard_policy import _castle_strategy_fit
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import card_matches_suit, hand_rules_for_state
from games.balatro.live.boss_hand_constraints import (
    constrain_boss_hand_plans,
    mouth_discard_fit,
    mouth_discard_only_decision,
)
from games.balatro.live.hand_action_policy import CLEAR_PATH, PACE_PLAY, PACE_RECOVERY
from games.balatro.live.hand_build_policy import BuildAwareLiveHandActionPolicy
from games.balatro.strategy_execution_guard_policy import (
    HAND_REPETITION_FIT,
    _clear_probability_tolerance,
    _green_preserving_play,
    _plan_clear_probability,
    _play_repeats_hand,
)
from games.balatro.target_hand_engine_policy import _target_hand_strategy_fit


_RANK_VALUE = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
    "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

_REALIZATION_WEIGHT = {
    BondRealization.DORMANT: 0.00,
    BondRealization.PARTIAL: 0.25,
    BondRealization.ACTIVE: 0.75,
    BondRealization.MATURE: 1.25,
}

# Strategy fit is only a within-safe-choice preference. These values must never be
# large enough to replace pace/survival legality; the parent D1 hierarchy decides
# that before this signal is consulted.
_PINNED_HELD_CARD_VALUE = 1.25
_PINNED_RED_SEAL_HELD_BONUS = 0.40


def _boss_projection_unconfirmed(state, confirmed_clear_path) -> bool:
    boss_name = str(getattr(state, "boss_name", "") or "")
    blind_type = str(getattr(state, "blind_type", "") or "").upper()
    return (bool(boss_name) or blind_type == "BOSS") and confirmed_clear_path is None


def _with_bond_intent_cache(method):
    """Cache immutable Bond hand intents for exactly one D1 policy decision."""
    def cached_decide(self, state, plans, **kwargs):
        intents = tuple(self._hand_bond_intents(state))
        self._bond_d1_cached_state_id = id(state)
        self._bond_d1_cached_intents = intents
        try:
            return method(self, state, plans, **kwargs)
        finally:
            self._bond_d1_cached_state_id = None
            self._bond_d1_cached_intents = None

    return cached_decide


class StrategyAwareLiveHandActionPolicy(BuildAwareLiveHandActionPolicy):
    """Production D1 survival authority with Bond/composition pursuit beneath it.

    Red/White safe-pace semantics live here directly. The policy may use deeper
    full-blind search to rank candidates, but that search cannot override a
    deterministic current-hand clear, a pace-qualified current PLAY, or the need to
    recover with a legal DISCARD when every current PLAY is below pace.
    """

    VAGABOND_PLAY_OPPORTUNITY_VALUE = 35.0
    PACE_STRATEGY_EQUIVALENCE_RATIO = 0.98

    def __init__(self, *args, strategy_tracker=None, **kwargs) -> None:
        del strategy_tracker
        super().__init__(*args, **kwargs)
        self._hand_evaluator = HandEvaluator()

    @_with_bond_intent_cache
    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        boss_unconfirmed = _boss_projection_unconfirmed(
            state,
            kwargs.get("confirmed_clear_path"),
        )
        if boss_unconfirmed:
            plans = tuple(
                replace(plan, exact=False) if bool(getattr(plan, "exact", False)) else plan
                for plan in plans
            )

        plans = constrain_boss_hand_plans(self, state, plans)
        if (
            plans
            and not any(plan.action.name == PLAY_CARDS for plan in plans)
            and any(plan.action.name == DISCARD_CARDS for plan in plans)
        ):
            forced = mouth_discard_only_decision(
                self,
                state,
                plans,
                search_attempts=kwargs.get("search_attempts", ()),
                setup_discard_consensus=kwargs.get("setup_discard_consensus", False),
            )
            if forced is not None:
                return forced

        decision = super().decide(state, plans, **kwargs)
        decision = self._enforce_safe_pace_scope(
            state,
            plans,
            decision,
            setup_discard_consensus=bool(kwargs.get("setup_discard_consensus", False)),
        )
        decision = self._refine_strategy_safe_pace(state, plans, decision)
        vagabond_active = self._vagabond_generation_active(state)
        if (
            decision.action.name == PLAY_CARDS
            and int(getattr(state, "hands_remaining", 0) or 0) <= 1
            and int(getattr(state, "discards_remaining", 0) or 0) > 0
            and (
                decision.selected_pace_ratio is None
                or float(decision.selected_pace_ratio) + self.EPSILON
                < float(self.thresholds.pace_ratio_floor)
            )
        ):
            discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
            if discards:
                self._ranking_state = state
                self.build_evaluator.prepare(state)
                try:
                    selected = max(
                        discards,
                        key=lambda plan: (
                            *self._within_type_key(plan),
                            float(self.evaluator.evaluate(state, plan.action)),
                        ),
                    )
                finally:
                    self._ranking_state = None
                    self.build_evaluator.reset_cache()
                decision = replace(
                    decision,
                    mode=PACE_RECOVERY,
                    action=selected.action,
                    selected_plan=selected,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=float(self.evaluator.evaluate(state, selected.action)),
                    confidence=max(float(decision.confidence), 0.95),
                    rationale=(
                        "final hand cannot currently clear the blind",
                        "legal discards remain, so playing an under-pace final hand would lose immediately",
                        "survival overrides all Bond/composition preferences",
                        "use the strongest full-blind D1 discard line and re-observe for a stronger final hand",
                        *decision.rationale,
                    ),
                )
        decision = self._green_preserved_decision(state, plans, decision)
        fit, rationale = self._strategy_fit(state, decision.action)
        decision = replace(
            decision,
            rationale=(
                *decision.rationale,
                *(("Vagabond active at <=$4 with consumable space; safe equivalent lines may value additional scored hands for Tarot generation only after normal D1 round resources tie",) if vagabond_active else ()),
                "canonical D1 action class is authoritative; Bond shaping cannot reverse Play/Discard survival arbitration",
                f"D1 Bond/composition fit={fit:+.3f}",
                *rationale,
            ),
        )
        if boss_unconfirmed and decision.mode == CLEAR_PATH:
            decision = replace(
                decision,
                confidence=min(float(decision.confidence), 0.95),
                rationale=(
                    "boss projection exactness is treated as model-dependent until independently confirmed",
                    *decision.rationale,
                ),
            )
        return decision

    @staticmethod
    def _deterministic_immediate_clear(plan, projection, score: float, remaining: float, epsilon: float) -> bool:
        if score + epsilon < remaining:
            return False
        probability = getattr(projection, "clear_probability", None)
        if probability is not None:
            return float(probability) >= 1.0 - epsilon
        outcomes = getattr(projection, "outcomes", None)
        if outcomes:
            try:
                return min(float(outcome.score) for outcome in outcomes) + epsilon >= remaining
            except (AttributeError, TypeError, ValueError):
                pass
        return bool(
            int(getattr(plan, "horizon", 0) or 0) <= 1
            and bool(getattr(plan, "exact", False))
            and float(plan.value.clear_probability) >= 1.0 - epsilon
        )

    def _green_preserved_decision(self, state, plans, decision):
        """Preserve Green inside canonical D1 when PLAY is survival-equivalent."""
        selected = _green_preserving_play(self, state, plans, decision)
        if selected is None:
            return decision

        score = float(self.evaluator.project_play(state, selected.action).expected_hand_score)
        pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
        pace_ratio = self._pace_ratio(score, pace_target)
        selected_probability = _plan_clear_probability(selected)
        discarded_probability = _plan_clear_probability(getattr(decision, "selected_plan", None))
        return replace(
            decision,
            action=selected.action,
            selected_plan=selected,
            selected_immediate_score=score,
            selected_pace_ratio=pace_ratio,
            selected_fallback_value=float(self.evaluator.evaluate(state, selected.action)),
            setup_discard_consensus=False,
            confidence=max(0.40, min(float(getattr(decision, "confidence", 0.40) or 0.40), 0.75)),
            rationale=(
                "Green Joker preservation: a PLAY is survival-equivalent to the selected discard",
                f"play clear probability={selected_probability:.3f}; discard={discarded_probability:.3f}; tolerance={_clear_probability_tolerance(decision):.3f}",
                "preserve Green's +Mult-on-play / -Mult-on-discard state when survival does not materially prefer the discard",
                "a materially safer discard still overrides Green Joker preservation",
                *decision.rationale,
            ),
        )

    def _enforce_safe_pace_scope(
        self,
        state,
        plans,
        baseline,
        *,
        setup_discard_consensus: bool,
    ):
        """Own Red/White Play-vs-Discard survival arbitration inside D1 itself.

        Deeper full-blind search remains useful evidence for ranking candidates, but
        it cannot switch the production objective away from immediate deterministic
        survival pacing. This logic previously lived in
        ``safe_pace_scope_correction`` as a late monkeypatch.
        """
        plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
        discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
        if not plays:
            return baseline

        pace_target = self._pace_target(state)
        hands_left = max(1, int(getattr(state, "hands_remaining", 1) or 1))
        remaining = max(0.0, pace_target * hands_left)
        projected = {
            id(plan): self.evaluator.project_play(state, plan.action)
            for plan in plays
        }
        scores = {
            id(plan): float(projected[id(plan)].expected_hand_score)
            for plan in plays
        }
        best_immediate = max(plays, key=lambda plan: scores[id(plan)])
        best_score = scores[id(best_immediate)]
        best_ratio = self._pace_ratio(best_score, pace_target)

        self._ranking_state = state
        self.build_evaluator.prepare(state)
        try:
            best_play = max(plays, key=self._within_type_key)
            best_discard = max(discards, key=self._within_type_key) if discards else None

            immediate_clears = tuple(
                plan
                for plan in plays
                if self._deterministic_immediate_clear(
                    plan,
                    projected[id(plan)],
                    scores[id(plan)],
                    remaining,
                    self.EPSILON,
                )
            )
            if immediate_clears:
                selected = max(immediate_clears, key=self._safe_equivalent_clear_key)
                selected_score = scores[id(selected)]
                return replace(
                    baseline,
                    mode=CLEAR_PATH,
                    action=selected.action,
                    selected_plan=selected,
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
                        "canonical safe-pace D1: current hand deterministically clears the blind",
                        "among deterministic clears, full-blind survival/resource ordering remains authoritative",
                        "multi-step engineered clear probability cannot override current-hand survival pacing",
                        *baseline.rationale,
                    ),
                )

            pace_plays = tuple(
                plan
                for plan in plays
                if self._pace_ratio(scores[id(plan)], pace_target) + self.EPSILON
                >= self.thresholds.pace_ratio_floor
            )
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
                return replace(
                    baseline,
                    mode=PACE_PLAY,
                    action=selected.action,
                    selected_plan=selected,
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
                        "canonical safe-pace D1: choose among current hands meeting remaining-score / hands-left pace",
                        "full-blind clear probability and plan quality rank pace-qualified plays",
                        "equal-safety held-resource and Bond strategy tie-breaks remain subordinate to survival",
                        *baseline.rationale,
                    ),
                )

            if discards and int(getattr(state, "discards_remaining", 0) or 0) > 0:
                selected = max(
                    discards,
                    key=lambda plan: (
                        *self._within_type_key(plan),
                        float(self.evaluator.evaluate(state, plan.action)),
                    ),
                )
                selected_value = float(self.evaluator.evaluate(state, selected.action))
                rationale = [
                    "canonical safe-pace D1: no current play meets remaining-score / hands-left pace",
                    "a legal discard remains, so do not burn a scoring hand below pace",
                    "full-blind plan quality ranks discard candidates before local discard value",
                ]
                if setup_discard_consensus:
                    rationale.append("deep adaptive searches also agree on the setup discard")
                return replace(
                    baseline,
                    mode=PACE_RECOVERY,
                    action=selected.action,
                    selected_plan=selected,
                    best_play=best_play,
                    best_discard=best_discard,
                    pace_target=pace_target,
                    best_play_immediate_score=best_score,
                    best_play_pace_ratio=best_ratio,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=selected_value,
                    clear_path_candidates=0,
                    sampled_clear_path_confirmed=False,
                    setup_discard_consensus=setup_discard_consensus,
                    confidence=0.75 if setup_discard_consensus else 0.60,
                    rationale=tuple(rationale) + baseline.rationale,
                )

            selected = best_play
            selected_score = scores[id(selected)]
            selected_ratio = self._pace_ratio(selected_score, pace_target)
            return replace(
                baseline,
                mode=PACE_RECOVERY,
                action=selected.action,
                selected_plan=selected,
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
                    "canonical safe-pace D1: no current play meets pace and no discard remains",
                    "forced recovery uses the strongest full-blind D1 plan; immediate score is secondary",
                    *baseline.rationale,
                ),
            )
        finally:
            self._ranking_state = None
            self.build_evaluator.reset_cache()

    def _refine_strategy_safe_pace(self, state, plans, decision):
        """Keep strategy tie-breaking inside a score/survival-equivalent PACE_PLAY band.

        This is canonical D1 policy behavior, not a post-policy correction layer.
        Strategy/Bond evidence may choose among pace-qualified plays only when the
        candidate remains within 98% of the strongest immediate score and within
        the configured clear-probability tolerance of the selected survival line.
        """
        if decision.mode != PACE_PLAY or decision.action.name != PLAY_CARDS:
            return decision

        plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
        if len(plays) < 2:
            return decision

        pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
        scores = {
            id(plan): float(self.evaluator.project_play(state, plan.action).expected_hand_score)
            for plan in plays
        }
        pace_qualified = tuple(
            plan
            for plan in plays
            if self._pace_ratio(scores[id(plan)], pace_target) + self.EPSILON
            >= self.thresholds.pace_ratio_floor
        )
        if len(pace_qualified) < 2:
            return decision

        best_score = max(scores[id(plan)] for plan in pace_qualified)
        minimum_score = max(
            pace_target * float(self.thresholds.pace_ratio_floor),
            best_score * self.PACE_STRATEGY_EQUIVALENCE_RATIO,
        )
        selected_probability = float(
            getattr(getattr(decision.selected_plan, "value", None), "clear_probability", 0.0)
            or 0.0
        )
        tolerance = float(
            getattr(decision.thresholds, "safe_clear_probability_tolerance", 0.0)
            or 0.0
        )
        equivalent = tuple(
            plan
            for plan in pace_qualified
            if scores[id(plan)] + self.EPSILON >= minimum_score
            and float(getattr(getattr(plan, "value", None), "clear_probability", 0.0) or 0.0)
            + tolerance
            + self.EPSILON
            >= selected_probability
        )
        if len(equivalent) < 2:
            return decision

        self._ranking_state = state
        self.build_evaluator.prepare(state)
        try:
            selected = max(
                equivalent,
                key=lambda plan: self._pace_play_key(
                    plan,
                    self._pace_ratio(scores[id(plan)], pace_target),
                ),
            )
        finally:
            self._ranking_state = None
            self.build_evaluator.reset_cache()
        if selected is decision.selected_plan:
            return decision

        selected_score = scores[id(selected)]
        selected_ratio = self._pace_ratio(selected_score, pace_target)
        selected_clear = float(
            getattr(getattr(selected, "value", None), "clear_probability", 0.0)
            or 0.0
        )
        return replace(
            decision,
            action=selected.action,
            selected_plan=selected,
            selected_immediate_score=selected_score,
            selected_pace_ratio=selected_ratio,
            confidence=self._pace_confidence(selected_ratio),
            rationale=(
                *decision.rationale,
                f"canonical strategy-safe pace band: selected score={selected_score:.3f}, best={best_score:.3f}, floor={self.PACE_STRATEGY_EQUIVALENCE_RATIO:.3f}x best",
                f"strategy line clear probability={selected_clear:.3f}; baseline={selected_probability:.3f}; tolerance={tolerance:.3f}",
                "Bond/composition may break only score- and survival-equivalent PACE_PLAY ties",
            ),
        )

    def _within_type_key(self, plan):
        base = super()._within_type_key(plan)
        strategy_fit = 0.0
        if self._ranking_state is None:
            original = base
        else:
            strategy_fit, _ = self._strategy_fit(self._ranking_state, plan.action)
            vagabond_hand_use = (
                -float(plan.value.expected_hands_remaining)
                if self._vagabond_generation_active(self._ranking_state)
                and plan.action.name == PLAY_CARDS
                else 0.0
            )
            original = (*base[:-1], strategy_fit, vagabond_hand_use, base[-1])

        if (
            plan.action.name == DISCARD_CARDS
            and float(plan.value.clear_probability) < 1.0 - self.EPSILON
        ):
            quality = (
                float(plan.value.clear_probability),
                float(plan.value.expected_progress),
                float(plan.value.expected_hands_remaining),
                float(plan.value.expected_discards_remaining),
                float(plan.value.expected_score),
                1 if bool(plan.exact) else 0,
            )
            zero_signal = (
                float(plan.value.clear_probability) <= self.EPSILON
                and float(plan.value.expected_progress) <= self.EPSILON
                and float(plan.value.expected_score) <= self.EPSILON
            )
            if zero_signal:
                return (
                    *quality,
                    strategy_fit,
                    len(getattr(plan.action, "cards", ()) or ()),
                    original,
                )
            return (*quality, original)
        return original

    def _safe_equivalent_clear_key(self, plan):
        base = super()._safe_equivalent_clear_key(plan)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        vagabond_hand_use = (
            -float(plan.value.expected_hands_remaining)
            if self._vagabond_generation_active(self._ranking_state)
            and plan.action.name == PLAY_CARDS
            else 0.0
        )
        return (*base[:-1], fit, vagabond_hand_use, base[-1])

    def _pace_play_key(self, plan, pace_ratio: float):
        base = super()._pace_play_key(plan, pace_ratio)
        if self._ranking_state is None:
            return base
        fit, _ = self._strategy_fit(self._ranking_state, plan.action)
        return (*base[:-1], fit, base[-1])

    @staticmethod
    def _vagabond_generation_active(state) -> bool:
        if int(getattr(state, "money", 0) or 0) > 4:
            return False
        if not any(type(joker).__name__ == "VagabondJoker" for joker in getattr(state, "jokers", ()) or ()):
            return False
        consumable_slots = int(getattr(state, "consumable_slots", 2) or 2)
        return len(getattr(state, "consumables", ()) or ()) < consumable_slots

    @staticmethod
    def _bond_weight(development) -> float:
        if not development.unlocked or development.rank < BondRank.R1:
            return 0.0
        rank = float(int(development.rank))
        realization = _REALIZATION_WEIGHT[development.realization]
        progress = 0.0
        if development.next_rank_threshold:
            progress = min(0.75, max(0.0, float(development.contribution) / float(development.next_rank_threshold)))
        return rank + realization + progress

    def _composition(self, state):
        try:
            return evaluate_bond_composition(state)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return (), None

    def _hand_bond_intents(self, state) -> list[tuple[str, float, str]]:
        if getattr(self, "_bond_d1_cached_state_id", None) == id(state):
            cached = getattr(self, "_bond_d1_cached_intents", None)
            if cached is not None:
                return list(cached)

        developments, composition = self._composition(state)
        if composition is None:
            return []
        selected = set(composition.bond_ids)
        intents: list[tuple[str, float, str]] = []
        for development in developments:
            target = str(development.target or "").upper()
            if not target or development.bond_id not in selected:
                continue
            weight = self._bond_weight(development)
            if weight > 0.0:
                intents.append((target, weight, development.bond_id))
        return intents

    @staticmethod
    def _pinned_candidate(composition):
        if composition is None:
            return None
        pinned_id = getattr(composition, "pinned_strategy_id", None)
        if not pinned_id:
            return None
        return next(
            (
                candidate
                for candidate in getattr(composition, "strategy_candidates", ()) or ()
                if candidate.strategy_id == pinned_id and candidate.pinned
            ),
            None,
        )

    @classmethod
    def _pinned_held_card_value(cls, candidate, card) -> tuple[float, tuple[str, ...]]:
        """Return strategic held value of one card for the pinned engine.

        Held-oriented candidate Bonds supply the semantic context. Rank/enhancement
        membership is derived from the candidate itself rather than a Joker-pair
        lookup, so any future held-King/Queen/Steel package inherits the behavior.
        """
        if candidate is None:
            return 0.0, ()
        bonds = set(candidate.bond_ids)
        prescriptions = tuple(str(item) for item in candidate.prescriptions)
        held_oriented = bool(bonds & {"held_cards", "held_retrigger"}) or any(
            "held" in item for item in prescriptions
        )
        if not held_oriented:
            return 0.0, ()

        rank = str(getattr(card, "rank", "") or "").upper()
        enhancement = str(getattr(card, "enhancement", "") or "").lower()
        seal = str(getattr(card, "seal", "") or "").lower()
        value = 0.0
        reasons: list[str] = []

        rank_bonds = {"K": "kings", "Q": "queens", "A": "aces", "J": "jacks"}
        rank_bond = rank_bonds.get(rank)
        if rank_bond and rank_bond in bonds:
            value += _PINNED_HELD_CARD_VALUE
            reasons.append(f"pinned {candidate.strategy_id} preserves held {rank}")
        if enhancement == "steel" and "steel" in bonds:
            value += _PINNED_HELD_CARD_VALUE
            reasons.append(f"pinned {candidate.strategy_id} preserves held Steel")
        if seal == "red" and value > 0.0 and "held_retrigger" in bonds:
            value += _PINNED_RED_SEAL_HELD_BONUS
            reasons.append("Red Seal amplifies pinned held engine")
        return value, tuple(reasons)

    def _pinned_card_preservation(self, state, action) -> tuple[float, tuple[str, ...]]:
        _, composition = self._composition(state)
        candidate = self._pinned_candidate(composition)
        if candidate is None or action.name not in {PLAY_CARDS, DISCARD_CARDS}:
            return 0.0, ()

        sacrificed = tuple(action.cards)
        total = 0.0
        notes: list[str] = []
        for card in sacrificed:
            value, reasons = self._pinned_held_card_value(candidate, card)
            total += value
            notes.extend(reasons)
        if total <= 0.0:
            return 0.0, (f"pinned strategy {candidate.strategy_id} sacrifices no held-engine card",)
        return -total, tuple(dict.fromkeys(notes))

    def _strategy_fit(self, state, action) -> tuple[float, tuple[str, ...]]:
        value, rationale = self._strategy_fit_without_castle(state, action)
        castle_value, castle_rationale = _castle_strategy_fit(state, action)
        burnt_value, burnt_rationale = _burnt_strategy_fit(
            state,
            action,
            hand_evaluator=self._hand_evaluator,
        )
        dna_value, dna_rationale = _dna_aces_fit(self, state, action)
        if dna_value > 0.0:
            dna_rationale = (
                *dna_rationale,
                f"DNA/Aces candidate evidence={dna_value:+.3f}; canonical D1 survival ordering remains authoritative",
            )
        repetition_value = HAND_REPETITION_FIT if _play_repeats_hand(self, state, action) else 0.0
        repetition_rationale = (
            (
                "realized hand_repetition evidence: this PLAY repeats a hand already used this round",
                "repetition fit is consulted only inside canonical D1 safe/equivalent candidate ranking",
            )
            if repetition_value > 0.0
            else ()
        )
        target_value, target_rationale = _target_hand_strategy_fit(self, state, action)
        mouth_value, mouth_rationale = mouth_discard_fit(self, state, action)
        return (
            value
            + castle_value
            + burnt_value
            + dna_value
            + repetition_value
            + target_value
            + mouth_value,
            (
                *rationale,
                *castle_rationale,
                *burnt_rationale,
                *dna_rationale,
                *repetition_rationale,
                *target_rationale,
                *mouth_rationale,
            ),
        )

    def _strategy_fit_without_castle(self, state, action) -> tuple[float, tuple[str, ...]]:
        intents = self._hand_bond_intents(state)
        preservation, preservation_notes = self._pinned_card_preservation(state, action)
        rules = hand_rules_for_state(state)

        if action.name == PLAY_CARDS:
            hand_type = self._hand_evaluator.evaluate(
                list(action.cards),
                rules=rules,
            ).value
            matches = [(weight, source) for target, weight, source in intents if target == str(hand_type).upper()]
            if not matches:
                return preservation, (
                    f"no developed Bond targets {hand_type}",
                    f"pinned held-card preservation={preservation:+.3f}",
                    *preservation_notes,
                )
            weight, source = max(matches)
            return weight + preservation, (
                f"D1 {source} Bond targets {hand_type} weight={weight:.3f}",
                f"pinned held-card preservation={preservation:+.3f}",
                *preservation_notes,
            )

        if action.name != DISCARD_CARDS:
            return preservation, ("D1 action has no Bond hand-structure signal", *preservation_notes)

        removed = {id(card) for card in action.cards}
        kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
        if not intents:
            return preservation, (
                "no developed hand-target Bond for discard shaping",
                f"pinned held-card preservation={preservation:+.3f}",
                *preservation_notes,
            )
        scored = [
            (
                self._structure_fit(kept, hand_type, rules=rules) * weight,
                self._structure_fit(kept, hand_type, rules=rules),
                hand_type,
                weight,
                source,
            )
            for hand_type, weight, source in intents
        ]
        value, structure, hand_type, weight, source = max(scored, key=lambda item: (item[0], item[1], item[3], item[2]))
        return value + preservation, (
            f"D1 discard preserves {hand_type} structure={structure:.3f}",
            f"D1 Bond intent source={source} weight={weight:.3f}",
            f"pinned held-card preservation={preservation:+.3f}",
            *preservation_notes,
        )

    @classmethod
    def _structure_fit(cls, cards, hand_type: str, *, rules: dict | None = None) -> float:
        rules = dict(rules or {})
        hand_type = str(hand_type).upper()
        regular = [
            card
            for card in cards
            if str(getattr(card, "enhancement", "") or "") != "Stone"
        ]
        ranks = Counter(str(getattr(card, "rank", "")) for card in regular)
        rank_counts = sorted(ranks.values(), reverse=True)
        maximum_rank = rank_counts[0] if rank_counts else 0
        flush_required = max(1, int(rules.get("flush_size", 5) or 5))
        maximum_suit = max(
            (
                sum(1 for card in regular if card_matches_suit(card, suit, rules))
                for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
            ),
            default=0,
        )
        if hand_type == "HIGH_CARD": return 0.25 if regular else 0.0
        if hand_type == "PAIR": return min(1.0, maximum_rank / 2.0)
        if hand_type == "TWO_PAIR": return min(1.0, sum(1 for count in rank_counts if count >= 2) / 2.0)
        if hand_type == "THREE_OF_A_KIND": return min(1.0, maximum_rank / 3.0)
        if hand_type == "FOUR_OF_A_KIND": return min(1.0, maximum_rank / 4.0)
        if hand_type == "FIVE_OF_A_KIND": return min(1.0, maximum_rank / 5.0)
        if hand_type == "FLUSH": return min(1.0, maximum_suit / float(flush_required))
        if hand_type == "STRAIGHT": return cls._straight_fit(regular, rules=rules)
        if hand_type == "FULL_HOUSE":
            top = rank_counts[0] if rank_counts else 0
            second = rank_counts[1] if len(rank_counts) > 1 else 0
            return 0.6 * min(1.0, top / 3.0) + 0.4 * min(1.0, second / 2.0)
        if hand_type == "STRAIGHT_FLUSH":
            return max(
                (
                    cls._straight_fit(
                        [card for card in regular if card_matches_suit(card, suit, rules)],
                        rules=rules,
                    )
                    for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
                ),
                default=0.0,
            )
        if hand_type == "FLUSH_HOUSE": return cls._structure_fit(regular, "FULL_HOUSE", rules=rules) * cls._structure_fit(regular, "FLUSH", rules=rules)
        if hand_type == "FLUSH_FIVE": return cls._structure_fit(regular, "FIVE_OF_A_KIND", rules=rules) * cls._structure_fit(regular, "FLUSH", rules=rules)
        return 0.0

    @staticmethod
    def _straight_fit(cards, *, rules: dict | None = None) -> float:
        rules = dict(rules or {})
        required = max(1, int(rules.get("straight_size", 5) or 5))
        max_step = 2 if bool(rules.get("shortcut")) else 1
        raw_values = {
            _RANK_VALUE.get(str(getattr(card, "rank", "")))
            for card in cards
        }
        raw_values.discard(None)
        if not raw_values:
            return 0.0

        value_sets = [set(raw_values)]
        if 14 in raw_values:
            ace_low = set(raw_values)
            ace_low.remove(14)
            ace_low.add(1)
            value_sets.append(ace_low)

        best = 1
        for values in value_sets:
            ordered = sorted(values)
            for start in range(len(ordered)):
                length = 1
                previous = ordered[start]
                for current in ordered[start + 1:]:
                    gap = current - previous
                    if 1 <= gap <= max_step:
                        length += 1
                        previous = current
                    elif gap > max_step:
                        break
                best = max(best, length)
        return min(1.0, best / float(required))
