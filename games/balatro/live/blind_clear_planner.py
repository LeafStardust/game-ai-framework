from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import perf_counter

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.card_selector import CardSelector
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.discard_projection import LiveDiscardJokerProjector
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.play_projection import LivePlayProjection
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class LiveBlindPlanValue:
    clear_probability: float
    expected_progress: float
    expected_score: float
    expected_hands_remaining: float
    expected_discards_remaining: float
    expected_consumables: float


@dataclass(frozen=True)
class LiveBlindPlan:
    action: BalatroAction
    value: LiveBlindPlanValue
    nodes_evaluated: int
    horizon: int
    sample_count: int
    budget_exceeded: bool = False


@dataclass(frozen=True)
class LiveBlindSearchBudget:
    max_nodes: int = 750
    max_seconds: float = 1.75
    root_beam_width: int = 12
    child_beam_width: int = 8
    max_root_discards: int = 8
    max_child_discards: int = 5
    draw_sample_count: int = 8

    def __post_init__(self) -> None:
        if self.max_nodes <= 0:
            raise ValueError("max_nodes must be positive")
        if self.max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        if self.root_beam_width <= 0:
            raise ValueError("root_beam_width must be positive")
        if self.child_beam_width <= 0:
            raise ValueError("child_beam_width must be positive")
        if self.max_root_discards < 0 or self.max_child_discards < 0:
            raise ValueError("discard beam widths must be non-negative")
        if self.draw_sample_count <= 0:
            raise ValueError("draw_sample_count must be positive")


class _SearchBudgetExceeded(RuntimeError):
    pass


class LiveBlindClearPlanner:
    """Bounded public-state planner for live Balatro blind clearing."""

    def __init__(
        self,
        evaluator,
        *,
        action_generator=None,
        card_selector: CardSelector | None = None,
        discard_projector: LiveDiscardJokerProjector | None = None,
        draw_outcomes: PublicDrawOutcomeModel | None = None,
        budget: LiveBlindSearchBudget | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.action_generator = action_generator or getattr(evaluator, "action_generator", None)
        if self.action_generator is None:
            raise ValueError("live blind planner requires an action generator")
        self.card_selector = card_selector or CardSelector()
        self.discard_projector = discard_projector or LiveDiscardJokerProjector()
        self.draw_outcomes = draw_outcomes or PublicDrawOutcomeModel()
        self.budget = budget or LiveBlindSearchBudget()
        self.nodes_evaluated = 0
        self.deadline = 0.0
        self.budget_exceeded = False

    def plan(
        self,
        state: BalatroState,
        *,
        horizon: int = 2,
        sample_count: int | None = None,
        allow_discards: bool = True,
    ) -> LiveBlindPlan | None:
        if state.phase != "SELECTING_HAND":
            return None
        if horizon <= 0:
            raise ValueError("horizon must be positive")

        self.nodes_evaluated = 0
        self.budget_exceeded = False
        self.deadline = perf_counter() + float(self.budget.max_seconds)
        sample_count = int(sample_count or self.budget.draw_sample_count)
        if sample_count <= 0:
            raise ValueError("sample_count must be positive")

        root_actions = self._candidate_actions(
            state,
            allow_discards=allow_discards,
            play_limit=self.budget.root_beam_width,
            discard_limit=self.budget.max_root_discards,
        )
        if not root_actions:
            return None

        best_action = None
        best_value = None
        try:
            for action in root_actions:
                self._check_deadline()
                value = self._estimate_action(
                    state,
                    action,
                    horizon=horizon,
                    sample_count=sample_count,
                    allow_discards=allow_discards,
                )
                if best_value is None or self._value_key(value) > self._value_key(best_value):
                    best_action = action
                    best_value = value
        except _SearchBudgetExceeded:
            self.budget_exceeded = True

        if best_action is None or best_value is None:
            fallback = root_actions[0]
            best_action = fallback
            best_value = self._fallback_action_value(state, fallback)

        return LiveBlindPlan(
            action=best_action,
            value=best_value,
            nodes_evaluated=self.nodes_evaluated,
            horizon=int(horizon),
            sample_count=sample_count,
            budget_exceeded=bool(self.budget_exceeded),
        )

    def _estimate_action(
        self,
        state: BalatroState,
        action: BalatroAction,
        *,
        horizon: int,
        sample_count: int,
        allow_discards: bool,
    ) -> LiveBlindPlanValue:
        self._consume_node()
        if action.name == PLAY_CARDS:
            return self._estimate_play(
                state,
                action,
                horizon=horizon,
                sample_count=sample_count,
                allow_discards=allow_discards,
            )
        if action.name == DISCARD_CARDS:
            return self._estimate_discard(
                state,
                action,
                horizon=horizon,
                sample_count=sample_count,
                allow_discards=allow_discards,
            )
        return self._zero_value()

    def _estimate_play(
        self,
        state: BalatroState,
        action: BalatroAction,
        *,
        horizon: int,
        sample_count: int,
        allow_discards: bool,
    ) -> LiveBlindPlanValue:
        projection: LivePlayProjection = self.evaluator.project_play(state, action)
        immediate_clear = float(projection.clear_probability)
        if immediate_clear >= 1.0 - 1e-12:
            return LiveBlindPlanValue(
                clear_probability=1.0,
                expected_progress=1.0,
                expected_score=float(getattr(state, "score", 0)) + float(projection.expected_hand_score),
                expected_hands_remaining=max(0.0, float(getattr(state, "hands_remaining", 0) - 1)),
                expected_discards_remaining=float(getattr(state, "discards_remaining", 0)),
                expected_consumables=float(len(getattr(state, "consumables", ()) or ())),
            )

        score_outcomes = tuple(getattr(projection, "score_outcomes", ()) or ())
        if not score_outcomes:
            score_outcomes = (projection,)

        aggregate = self._zero_value()
        probability_total = 0.0
        for score_outcome in score_outcomes:
            probability = float(getattr(score_outcome, "probability", 1.0) or 0.0)
            if probability <= 0:
                continue
            probability_total += probability
            next_state = self._score_outcome_state(score_outcome, state)
            score_delta = float(
                getattr(
                    score_outcome,
                    "hand_score",
                    getattr(score_outcome, "expected_hand_score", projection.expected_hand_score),
                )
                or 0.0
            )
            projected_state = next_state.copy()
            projected_state.score = int(getattr(next_state, "score", getattr(state, "score", 0)) or 0) + int(score_delta)
            projected_state.hands_remaining = max(0, int(getattr(next_state, "hands_remaining", getattr(state, "hands_remaining", 0)) or 0) - 1)

            clear = self._target(projected_state) > 0 and int(projected_state.score) >= self._target(projected_state)
            if clear or horizon <= 1 or projected_state.hands_remaining <= 0:
                continuation = self._terminal_value(projected_state, clear=clear)
            else:
                continuation = self._best_continuation(
                    projected_state,
                    horizon=horizon - 1,
                    sample_count=sample_count,
                    allow_discards=allow_discards,
                )
            aggregate = self._add_weighted(aggregate, continuation, probability)

        if probability_total <= 0:
            return self._terminal_value(state, clear=False)
        return self._scale_value(aggregate, 1.0 / probability_total)

    def _estimate_discard(
        self,
        state: BalatroState,
        action: BalatroAction,
        *,
        horizon: int,
        sample_count: int,
        allow_discards: bool,
    ) -> LiveBlindPlanValue:
        if int(getattr(state, "discards_remaining", 0)) <= 0:
            return self._terminal_value(state, clear=False)

        projected = self.discard_projector.project(state, action)
        if projected is None:
            return self._terminal_value(state, clear=False)

        deck = PublicDeckComposition.from_state(projected)
        outcomes = self.draw_outcomes.sample(
            deck,
            draw_count=len(action.cards),
            sample_count=sample_count,
        )
        if not outcomes:
            return self._terminal_value(projected, clear=False)

        aggregate = self._zero_value()
        probability_total = 0.0
        for outcome in outcomes:
            probability = float(getattr(outcome, "probability", 0.0) or 0.0)
            if probability <= 0:
                continue
            probability_total += probability
            drawn = tuple(getattr(outcome, "cards", ()) or ())
            child = projected.copy()
            hand = list(getattr(projected, "hand", ()) or ())
            hand.extend(drawn)
            child.hand = hand
            child.discards_remaining = max(0, int(getattr(projected, "discards_remaining", 0)) - 1)
            if horizon <= 1:
                continuation = self._terminal_value(child, clear=False)
            else:
                continuation = self._best_continuation(
                    child,
                    horizon=horizon - 1,
                    sample_count=sample_count,
                    allow_discards=allow_discards,
                )
            aggregate = self._add_weighted(aggregate, continuation, probability)

        if probability_total <= 0:
            return self._terminal_value(projected, clear=False)
        return self._scale_value(aggregate, 1.0 / probability_total)

    def _best_continuation(
        self,
        state: BalatroState,
        *,
        horizon: int,
        sample_count: int,
        allow_discards: bool,
    ) -> LiveBlindPlanValue:
        actions = self._candidate_actions(
            state,
            allow_discards=allow_discards,
            play_limit=self.budget.child_beam_width,
            discard_limit=self.budget.max_child_discards,
        )
        if not actions:
            return self._terminal_value(state, clear=False)

        best = None
        for action in actions:
            self._check_deadline()
            value = self._estimate_action(
                state,
                action,
                horizon=horizon,
                sample_count=sample_count,
                allow_discards=allow_discards,
            )
            if best is None or self._value_key(value) > self._value_key(best):
                best = value
        return best or self._terminal_value(state, clear=False)

    def _candidate_actions(
        self,
        state: BalatroState,
        *,
        allow_discards: bool,
        play_limit: int,
        discard_limit: int,
    ) -> list[BalatroAction]:
        self._check_deadline()
        plays = self.action_generator.generate_play_actions(state)
        self._check_deadline()
        initial_root = self.nodes_evaluated == 0
        soft_deadline = self.deadline
        ranked_plays = self._rank_actions_with_deadline(
            state,
            plays,
            priority=self._root_play_priority if initial_root else self._play_priority,
            limit=play_limit,
            soft_deadline=soft_deadline if initial_root else None,
        )
        if (
            not allow_discards
            or discard_limit <= 0
            or int(getattr(state, "discards_remaining", 0)) <= 0
        ):
            return ranked_plays

        self._check_deadline()
        discards = self.action_generator.generate_discard_actions(state)
        self._check_deadline()
        ranked_discards = self._rank_actions_with_deadline(
            state,
            discards,
            priority=self._discard_priority,
            limit=discard_limit,
            soft_deadline=soft_deadline if initial_root else None,
        )
        return ranked_plays + ranked_discards

    def _root_play_priority(self, state, action: BalatroAction) -> tuple[float, float, int, int]:
        """Rank root beam candidates without full stochastic/Joker projection.

        Full ``project_play`` remains authoritative once a candidate enters the
        actual planner. Root admission only needs a deterministic public-state
        ordering, which prevents an uninterruptible projection from consuming the
        entire search budget before node zero is admitted.
        """
        ensure_cache = getattr(self.evaluator, "_ensure_outer_d1_cache", None)
        action_key = getattr(self.evaluator, "_action_key", None)
        if callable(ensure_cache) and callable(action_key):
            ensure_cache(state)
            projection_cache = getattr(self.evaluator, "_outer_d1_projection_cache", None)
            if isinstance(projection_cache, dict):
                cached = projection_cache.get(action_key(action))
                if cached is not None:
                    return (
                        float(cached.clear_probability),
                        float(cached.expected_hand_score),
                        int(cached.hand_score),
                        -len(action.cards),
                    )

        hand_for_cards = getattr(self.evaluator, "_hand_for_cards", None)
        scorer = getattr(self.evaluator, "scorer", None)
        if not callable(hand_for_cards) or scorer is None:
            # Minimal test/adapter evaluators need not expose Balatro scoring
            # internals. Keep root admission projection-free and deterministic.
            return (0.0, float(len(action.cards)), len(action.cards), -len(action.cards))

        hand = hand_for_cards(state, action.cards)
        base = scorer.SCORES[hand]
        scoring_cards = scorer.scoring_cards(
            hand,
            list(action.cards or []),
            rules=hand_rules_for_state(state),
        )
        card_chips = sum(
            scorer.card_chip_value(card)
            for card in scoring_cards
            if not scorer.is_card_debuffed(card)
        )
        literal_score = float((base.chips + card_chips) * base.mult * base.x_mult)
        remaining = max(
            0,
            self._target(state) - int(getattr(state, "score", 0) or 0),
        )
        literal_clear = 1.0 if remaining > 0 and literal_score >= remaining else 0.0
        return (
            literal_clear,
            literal_score,
            int(base.chips * base.mult),
            -len(action.cards),
        )

    def _play_priority(self, state, action: BalatroAction) -> tuple[float, float, int, int]:
        projection = self.evaluator.project_play(state, action)
        return (
            projection.clear_probability,
            projection.expected_hand_score,
            projection.hand_score,
            -len(action.cards),
        )

    def _discard_priority(self, state, action: BalatroAction) -> tuple[float, int]:
        return float(self.evaluator.evaluate(state, action)), len(action.cards)

    def _terminal_value(self, state, *, clear: bool) -> LiveBlindPlanValue:
        target = self._target(state)
        score = float(getattr(state, "score", 0))
        effective_clear = bool(clear or self._mr_bones_rescues(state))
        if target > 0:
            progress = min(1.0, max(0.0, score / target))
        else:
            progress = 0.0
        return LiveBlindPlanValue(
            clear_probability=1.0 if effective_clear else 0.0,
            expected_progress=1.0 if effective_clear else progress,
            expected_score=score,
            expected_hands_remaining=float(getattr(state, "hands_remaining", 0)),
            expected_discards_remaining=float(getattr(state, "discards_remaining", 0)),
            expected_consumables=float(len(getattr(state, "consumables", ()) or ())),
        )

    @staticmethod
    def _zero_value() -> LiveBlindPlanValue:
        return LiveBlindPlanValue(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    @staticmethod
    def _score_outcome_state(score_outcome, fallback_state):
        state = getattr(score_outcome, "state_after_scoring", None)
        return fallback_state if state is None else state

    @staticmethod
    def _value_key(value: LiveBlindPlanValue) -> tuple[float, float, float, float, float, float]:
        return (
            float(value.clear_probability),
            float(value.expected_progress),
            float(value.expected_score),
            float(value.expected_hands_remaining),
            float(value.expected_discards_remaining),
            float(value.expected_consumables),
        )

    @staticmethod
    def _add_weighted(
        left: LiveBlindPlanValue,
        right: LiveBlindPlanValue,
        weight: float,
    ) -> LiveBlindPlanValue:
        return LiveBlindPlanValue(
            clear_probability=left.clear_probability + right.clear_probability * weight,
            expected_progress=left.expected_progress + right.expected_progress * weight,
            expected_score=left.expected_score + right.expected_score * weight,
            expected_hands_remaining=left.expected_hands_remaining + right.expected_hands_remaining * weight,
            expected_discards_remaining=left.expected_discards_remaining + right.expected_discards_remaining * weight,
            expected_consumables=left.expected_consumables + right.expected_consumables * weight,
        )

    @staticmethod
    def _scale_value(value: LiveBlindPlanValue, scale: float) -> LiveBlindPlanValue:
        return LiveBlindPlanValue(
            clear_probability=value.clear_probability * scale,
            expected_progress=value.expected_progress * scale,
            expected_score=value.expected_score * scale,
            expected_hands_remaining=value.expected_hands_remaining * scale,
            expected_discards_remaining=value.expected_discards_remaining * scale,
            expected_consumables=value.expected_consumables * scale,
        )

    def _fallback_action_value(self, state, action: BalatroAction) -> LiveBlindPlanValue:
        if action.name == PLAY_CARDS:
            projection = self.evaluator.project_play(state, action)
            return LiveBlindPlanValue(
                clear_probability=float(projection.clear_probability),
                expected_progress=float(projection.clear_probability),
                expected_score=float(getattr(state, "score", 0)) + float(projection.expected_hand_score),
                expected_hands_remaining=max(0.0, float(getattr(state, "hands_remaining", 0) - 1)),
                expected_discards_remaining=float(getattr(state, "discards_remaining", 0)),
                expected_consumables=float(len(getattr(state, "consumables", ()) or ())),
            )
        return self._terminal_value(state, clear=False)

    def _rank_actions_with_deadline(
        self,
        state,
        actions,
        *,
        priority,
        limit: int,
        soft_deadline: float | None = None,
    ):
        ranked = []
        for action in actions:
            if soft_deadline is not None and perf_counter() >= soft_deadline:
                self.budget_exceeded = True
                break
            self._check_deadline()
            key = priority(state, action)
            if soft_deadline is not None and perf_counter() >= soft_deadline:
                self.budget_exceeded = True
            self._check_deadline()
            ranked.append((key, action))
            if soft_deadline is not None and self.budget_exceeded:
                break
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [action for _, action in ranked[: max(0, int(limit))]]

    def _consume_node(self) -> None:
        self._check_deadline()
        if self.nodes_evaluated >= int(self.budget.max_nodes):
            self.budget_exceeded = True
            raise _SearchBudgetExceeded("live blind planner node budget exceeded")
        self.nodes_evaluated += 1

    def _check_deadline(self) -> None:
        if self.deadline and perf_counter() >= self.deadline:
            self.budget_exceeded = True
            raise _SearchBudgetExceeded("live blind planner wall-clock budget exceeded")

    @staticmethod
    def _target(state) -> int:
        return max(0, int(getattr(state, "target_score", 0) or 0))

    @staticmethod
    def _mr_bones_rescues(state) -> bool:
        for joker in tuple(getattr(state, "jokers", ()) or ()):
            label = str(
                getattr(joker, "label", None)
                or getattr(joker, "name", None)
                or getattr(joker, "center", None)
                or ""
            ).lower()
            if "mr bones" in label or "mr_bones" in label:
                target = max(0, int(getattr(state, "target_score", 0) or 0))
                score = max(0, int(getattr(state, "score", 0) or 0))
                return target > 0 and score >= target * 0.25
        return False
