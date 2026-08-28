from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.card_selector import CardSelector
from games.balatro.live.discard_projection import LiveDiscardJokerProjector
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


class PlannerSearchBudgetExceeded(RuntimeError):
    """Raised when a bounded live planner search exhausts its search budget."""


@dataclass(frozen=True)
class LiveBlindPlanValue:
    clear_probability: float
    expected_progress: float
    expected_score: float
    expected_hands_remaining: float
    expected_discards_remaining: float
    # Free generated consumables (notably Purple Seal Tarot generation) are a
    # future-run resource. Keep them as a late tie-break rather than converting
    # them into invented chip-equivalent utility: survival/progress and remaining
    # hand/discard resources stay authoritative first.
    expected_consumables: float = 0.0

    def weighted(self, probability: float) -> "LiveBlindPlanValue":
        return LiveBlindPlanValue(
            clear_probability=self.clear_probability * probability,
            expected_progress=self.expected_progress * probability,
            expected_score=self.expected_score * probability,
            expected_hands_remaining=self.expected_hands_remaining * probability,
            expected_discards_remaining=self.expected_discards_remaining * probability,
            expected_consumables=self.expected_consumables * probability,
        )

    def plus(self, other: "LiveBlindPlanValue") -> "LiveBlindPlanValue":
        return LiveBlindPlanValue(
            clear_probability=self.clear_probability + other.clear_probability,
            expected_progress=self.expected_progress + other.expected_progress,
            expected_score=self.expected_score + other.expected_score,
            expected_hands_remaining=(
                self.expected_hands_remaining + other.expected_hands_remaining
            ),
            expected_discards_remaining=(
                self.expected_discards_remaining + other.expected_discards_remaining
            ),
            expected_consumables=(
                self.expected_consumables + other.expected_consumables
            ),
        )


@dataclass(frozen=True)
class LiveBlindPlan:
    action: BalatroAction
    value: LiveBlindPlanValue
    horizon: int
    exact: bool
    candidate_count: int


@dataclass(frozen=True)
class _ActionEstimate:
    action: BalatroAction
    value: LiveBlindPlanValue
    exact: bool


class LiveBlindClearPlanner:
    """Bounded expectimax planner over public live Balatro state.

    Replanning after each real checkpoint supplies the next horizon. Hidden draw
    order is never used. Validated stateful Joker transitions are carried between
    hypothetical play nodes on isolated branch copies.

    Root and child action beams can be configured independently. This matters for
    deeper live diagnostics: keeping a useful root comparison while narrowing
    recursive child choices prevents sampled redraw branches from exploding
    combinatorially. ``max_nodes`` provides a final hard safety cap.
    """

    DEFAULT_EXACT_DRAW_COMBINATION_LIMIT = 128
    DEFAULT_DRAW_SAMPLE_COUNT = 64
    ROOT_CANDIDATE_BOOTSTRAP_SECONDS = 0.75

    def __init__(
        self,
        *,
        evaluator: LiveHandDecisionEvaluator | None = None,
        action_generator: CardSelector | None = None,
        draw_outcomes: PublicDrawOutcomeModel | None = None,
        play_width: int = 6,
        discard_width: int = 4,
        child_play_width: int | None = None,
        child_discard_width: int | None = None,
        horizon: int = 2,
        max_nodes: int | None = None,
        deadline: float | None = None,
    ):
        if play_width < 1:
            raise ValueError("play_width must be positive")
        if discard_width < 0:
            raise ValueError("discard_width cannot be negative")
        if child_play_width is not None and child_play_width < 1:
            raise ValueError("child_play_width must be positive")
        if child_discard_width is not None and child_discard_width < 0:
            raise ValueError("child_discard_width cannot be negative")
        if horizon < 1:
            raise ValueError("horizon must be at least 1")
        if max_nodes is not None and max_nodes < 1:
            raise ValueError("max_nodes must be positive when supplied")

        self.evaluator = evaluator or LiveHandDecisionEvaluator()
        self.action_generator = action_generator or CardSelector()
        self.draw_outcomes = draw_outcomes or PublicDrawOutcomeModel(
            exact_combination_limit=self.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
            sample_count=self.DEFAULT_DRAW_SAMPLE_COUNT,
        )
        self.discard_joker_projector = LiveDiscardJokerProjector()
        self.play_width = int(play_width)
        self.discard_width = int(discard_width)
        self.child_play_width = int(
            play_width if child_play_width is None else child_play_width
        )
        self.child_discard_width = int(
            discard_width if child_discard_width is None else child_discard_width
        )
        self.horizon = int(horizon)
        self.max_nodes = int(max_nodes) if max_nodes is not None else None
        self.deadline = float(deadline) if deadline is not None else None
        self.nodes_evaluated = 0

    def reset_search_stats(self) -> None:
        self.nodes_evaluated = 0
        reset_root = getattr(self.draw_outcomes, "reset_root", None)
        if callable(reset_root):
            reset_root()

    def plan(self, state) -> LiveBlindPlan:
        self._require_state(state)
        self.reset_search_stats()
        candidates = self._candidate_actions(state, allow_discards=self.horizon > 1)
        if not candidates:
            raise RuntimeError("no live blind-clear candidate action is available")

        estimates = [
            self._estimate_action(state, action, self.horizon)
            for action in candidates
        ]
        best = max(estimates, key=self._estimate_key)
        return LiveBlindPlan(
            action=best.action,
            value=best.value,
            horizon=self.horizon,
            exact=best.exact,
            candidate_count=len(candidates),
        )

    def _check_deadline(self) -> None:
        if self.deadline is not None and perf_counter() >= self.deadline:
            raise PlannerSearchBudgetExceeded(
                "live blind planner search exceeded wall-clock budget"
            )

    def _consume_node(self) -> None:
        self._check_deadline()
        if self.max_nodes is not None and self.nodes_evaluated >= self.max_nodes:
            raise PlannerSearchBudgetExceeded(
                "live blind planner search exceeded node budget "
                f"({self.max_nodes})"
            )
        self.nodes_evaluated += 1

    def _best_value(self, state, depth: int) -> tuple[LiveBlindPlanValue, bool]:
        if self._is_cleared(state):
            return self._terminal_value(state, clear=True), True
        if int(getattr(state, "hands_remaining", 0)) <= 0:
            return self._terminal_value(state, clear=False), True
        if depth <= 0:
            return self._terminal_value(state, clear=False), True

        candidates = self._candidate_actions(
            state,
            allow_discards=depth > 1,
            play_width=self.child_play_width,
            discard_width=self.child_discard_width,
        )
        if not candidates:
            return self._terminal_value(state, clear=False), True

        estimates = [
            self._estimate_action(state, action, depth)
            for action in candidates
        ]
        best = max(estimates, key=self._estimate_key)
        return best.value, best.exact

    def _estimate_action(self, state, action: BalatroAction, depth: int) -> _ActionEstimate:
        self._consume_node()
        if action.name == PLAY_CARDS:
            return self._estimate_play(state, action, depth)
        if action.name == DISCARD_CARDS:
            return self._estimate_discard(state, action, depth)
        raise ValueError(f"unsupported live blind-clear action {action.name}")

    def _estimate_play(self, state, action: BalatroAction, depth: int) -> _ActionEstimate:
        projection = self.evaluator.project_play(state, action)
        total_value = self._zero_value()
        exact = projection.joker_projection_complete
        hands_after = max(0, int(getattr(state, "hands_remaining", 0)) - 1)
        target = self._target(state)
        played_indices = self._card_indices(state.hand, action.cards)
        projected_state = projection.state_after_scoring
        if projected_state is None:
            projected_state = deepcopy(state)

        if depth <= 1:
            for score_outcome in projection.outcomes:
                score_after = int(getattr(state, "score", 0)) + score_outcome.score
                outcome_state = self._score_outcome_state(score_outcome, projected_state)
                branch_state = deepcopy(outcome_state)
                branch_state.score = score_after
                branch_state.hands_remaining = hands_after
                value = self._terminal_value(
                    branch_state,
                    clear=(target > 0 and score_after >= target),
                )
                total_value = total_value.plus(value.weighted(score_outcome.probability))
            return _ActionEstimate(action, total_value, exact)

        retained_cards = [
            card
            for index, card in enumerate(projected_state.hand)
            if index not in played_indices
        ]
        joker_drawn_cards = max(
            0,
            len(getattr(projected_state, "hand", [])) - len(getattr(state, "hand", [])),
        )
        replacement_draw_count = max(0, len(action.cards) - joker_drawn_cards)
        composition = None
        draw_distribution = None

        for score_outcome in projection.outcomes:
            outcome_state = self._score_outcome_state(score_outcome, projected_state)
            score_after = int(getattr(state, "score", 0)) + score_outcome.score
            if target > 0 and score_after >= target:
                branch_state = deepcopy(outcome_state)
                branch_state.score = score_after
                branch_state.hands_remaining = hands_after
                total_value = total_value.plus(
                    self._terminal_value(branch_state, clear=True).weighted(score_outcome.probability)
                )
                continue

            if hands_after <= 0:
                branch_state = deepcopy(outcome_state)
                branch_state.score = score_after
                branch_state.hands_remaining = 0
                total_value = total_value.plus(
                    self._terminal_value(branch_state, clear=False).weighted(score_outcome.probability)
                )
                continue

            retained_state = deepcopy(outcome_state)
            retained_state.score = score_after
            retained_state.hands_remaining = hands_after
            retained_state.hand = list(retained_cards)
            guaranteed_value = self._guaranteed_next_play_value(retained_state)
            if guaranteed_value is not None:
                total_value = total_value.plus(guaranteed_value.weighted(score_outcome.probability))
                continue

            if replacement_draw_count <= 0:
                value, child_exact = self._best_value(retained_state, depth - 1)
                exact = exact and child_exact
                total_value = total_value.plus(value.weighted(score_outcome.probability))
                continue

            if draw_distribution is None:
                composition = PublicDeckComposition.from_state(state)
                draw_distribution = self.draw_outcomes.distribution(
                    composition,
                    replacement_draw_count,
                )
                exact = exact and draw_distribution.exact

            assert composition is not None
            assert draw_distribution is not None
            for draw_outcome in draw_distribution.outcomes:
                next_state = deepcopy(outcome_state)
                next_state.score = score_after
                next_state.hands_remaining = hands_after
                next_state.hand = list(retained_cards) + [
                    self.draw_outcomes.card_from_signature(signature)
                    for signature in draw_outcome.cards
                ]
                next_state.deck = self.draw_outcomes.remaining_cards(composition, draw_outcome)
                value, child_exact = self._best_value(next_state, depth - 1)
                exact = exact and child_exact
                probability = score_outcome.probability * draw_outcome.probability
                total_value = total_value.plus(value.weighted(probability))

        return _ActionEstimate(action, total_value, exact)

    def _guaranteed_next_play_value(self, state) -> LiveBlindPlanValue | None:
        """Return an exact clear value using only cards already retained in hand."""
        candidates = self._candidate_actions(
            state,
            allow_discards=False,
            play_width=self.child_play_width,
            discard_width=0,
        )
        if not candidates:
            return None

        estimates = [self._estimate_action(state, action, 1) for action in candidates]
        guaranteed = [
            estimate
            for estimate in estimates
            if estimate.exact and estimate.value.clear_probability >= 1.0 - 1e-12
        ]
        if not guaranteed:
            return None
        best = max(guaranteed, key=lambda estimate: self._value_key(estimate.value))
        return best.value

    def _estimate_discard(self, state, action: BalatroAction, depth: int) -> _ActionEstimate:
        if int(getattr(state, "discards_remaining", 0)) <= 0:
            return _ActionEstimate(
                action,
                LiveBlindPlanValue(-1.0, 0.0, 0.0, 0.0, 0.0),
                True,
            )

        discard_state = self.discard_joker_projector.project(state, action.cards)
        discards_after = max(0, int(state.discards_remaining) - 1)
        if depth <= 1:
            next_state = deepcopy(discard_state)
            next_state.discards_remaining = discards_after
            return _ActionEstimate(action, self._terminal_value(next_state, clear=False), True)

        composition = PublicDeckComposition.from_state(state)
        draw_distribution = self.draw_outcomes.distribution(composition, len(action.cards))
        removed_indices = self._card_indices(state.hand, action.cards)
        total_value = self._zero_value()
        exact = draw_distribution.exact

        for draw_outcome in draw_distribution.outcomes:
            next_state = deepcopy(discard_state)
            next_state.discards_remaining = discards_after
            kept = [
                card
                for index, card in enumerate(next_state.hand)
                if index not in removed_indices
            ]
            next_state.hand = kept + [
                self.draw_outcomes.card_from_signature(signature)
                for signature in draw_outcome.cards
            ]
            next_state.deck = self.draw_outcomes.remaining_cards(composition, draw_outcome)
            value, child_exact = self._best_value(next_state, depth - 1)
            exact = exact and child_exact
            total_value = total_value.plus(value.weighted(draw_outcome.probability))

        return _ActionEstimate(action, total_value, exact)

    def _rank_actions_with_deadline(
        self,
        state,
        actions,
        *,
        priority,
        limit: int,
        soft_deadline: float | None = None,
    ) -> list[BalatroAction]:
        scored = []
        for action in actions:
            self._check_deadline()
            if soft_deadline is not None and scored and perf_counter() >= soft_deadline:
                break
            score = priority(state, action)
            self._check_deadline()
            scored.append((score, action))
            if soft_deadline is not None and perf_counter() >= soft_deadline:
                break
        scored.sort(key=lambda item: item[0], reverse=True)
        return [action for _, action in scored[:limit]]

    def _candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ) -> list[BalatroAction]:
        play_limit = self.play_width if play_width is None else int(play_width)
        discard_limit = self.discard_width if discard_width is None else int(discard_width)

        initial_root = int(getattr(self, "nodes_evaluated", 0)) == 0
        soft_deadline = None
        if initial_root:
            soft_deadline = perf_counter() + self.ROOT_CANDIDATE_BOOTSTRAP_SECONDS
            if self.deadline is not None:
                soft_deadline = min(self.deadline, soft_deadline)

        self._check_deadline()
        plays = self.action_generator.generate_play_actions(state)
        self._check_deadline()
        ranked_plays = self._rank_actions_with_deadline(
            state,
            plays,
            priority=self._play_priority,
            limit=play_limit,
            soft_deadline=soft_deadline,
        )

        if initial_root and soft_deadline is not None and perf_counter() >= soft_deadline:
            return ranked_plays

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
    def _card_indices(hand, selected) -> set[int]:
        selected_ids = {id(card) for card in selected}
        return {
            index
            for index, card in enumerate(hand)
            if id(card) in selected_ids
        }

    @staticmethod
    def _kept_cards(hand, removed) -> list:
        removed_ids = {id(card) for card in removed}
        return [card for card in hand if id(card) not in removed_ids]

    @staticmethod
    def _target(state) -> int:
        return int(getattr(getattr(state, "blind", None), "requirement", 0))

    def _is_cleared(self, state) -> bool:
        target = self._target(state)
        return target > 0 and int(getattr(state, "score", 0)) >= target

    def _mr_bones_rescues(self, state) -> bool:
        if int(getattr(state, "hands_remaining", 0) or 0) > 0:
            return False

        target = self._target(state)
        score = int(getattr(state, "score", 0) or 0)
        if target <= 0 or score >= target or score * 4 < target:
            return False

        return any(
            type(joker).__name__ == "MrBonesJoker"
            for joker in getattr(state, "jokers", [])
        )

    @classmethod
    def _estimate_key(cls, estimate: _ActionEstimate) -> tuple[float, int, float, float, float, float, float]:
        """Rank survival first; exactness protects proven lines from sampled estimates."""
        value = estimate.value
        return (
            value.clear_probability,
            1 if estimate.exact else 0,
            value.expected_progress,
            value.expected_hands_remaining,
            value.expected_discards_remaining,
            value.expected_score,
            value.expected_consumables,
        )

    @staticmethod
    def _value_key(value: LiveBlindPlanValue) -> tuple[float, float, float, float, float, float]:
        return (
            value.clear_probability,
            value.expected_progress,
            value.expected_hands_remaining,
            value.expected_discards_remaining,
            value.expected_score,
            value.expected_consumables,
        )

    @staticmethod
    def _require_state(state) -> None:
        if getattr(state, "phase", None) != "SELECTING_HAND":
            raise ValueError("live blind-clear planning requires SELECTING_HAND phase")
        if not getattr(state, "hand", None):
            raise ValueError("live blind-clear planning requires a visible hand")
        if int(getattr(state, "hands_remaining", 0)) <= 0:
            raise ValueError("live blind-clear planning requires at least one hand")
