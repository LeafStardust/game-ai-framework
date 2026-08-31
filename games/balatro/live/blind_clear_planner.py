from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.card_selector import CardSelector
from games.balatro.d1_hook_search_budget_policy import _active_hook
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.discard_projection import LiveDiscardJokerProjector
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


_ROOT_PLAY_PREFILTER = 64
_CHILD_PLAY_PREFILTER = 24
_ROOT_DISCARD_PREFILTER = 14
_CHILD_DISCARD_PREFILTER = 8
_SHORT_PLAY_RESERVE = 2
_WIDE_DISCARD_RESERVE = 2
_ROOT_DISCARD_RESERVE = 2
_EPSILON = 1e-12

_HAND_STRENGTH = {
    PokerHand.HIGH_CARD: 0,
    PokerHand.PAIR: 1,
    PokerHand.TWO_PAIR: 2,
    PokerHand.THREE_OF_A_KIND: 3,
    PokerHand.STRAIGHT: 4,
    PokerHand.FLUSH: 5,
    PokerHand.FULL_HOUSE: 6,
    PokerHand.FOUR_OF_A_KIND: 7,
    PokerHand.STRAIGHT_FLUSH: 8,
    PokerHand.FIVE_OF_A_KIND: 9,
    PokerHand.FLUSH_HOUSE: 10,
    PokerHand.FLUSH_FIVE: 11,
}

_RANK_VALUES = {
    "A": 14,
    "ACE": 14,
    "K": 13,
    "KING": 13,
    "Q": 12,
    "QUEEN": 12,
    "J": 11,
    "JACK": 11,
    "10": 10,
    "9": 9,
    "8": 8,
    "7": 7,
    "6": 6,
    "5": 5,
    "4": 4,
    "3": 3,
    "2": 2,
}


class PlannerSearchBudgetExceeded(RuntimeError):
    """Raised when a bounded live planner search exhausts its search budget."""


@dataclass(frozen=True)
class LiveBlindPlanValue:
    clear_probability: float
    expected_progress: float
    expected_score: float
    expected_hands_remaining: float
    expected_discards_remaining: float
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
            expected_hands_remaining=self.expected_hands_remaining + other.expected_hands_remaining,
            expected_discards_remaining=self.expected_discards_remaining + other.expected_discards_remaining,
            expected_consumables=self.expected_consumables + other.expected_consumables,
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
    """Bounded expectimax planner over public live Balatro state."""

    DEFAULT_EXACT_DRAW_COMBINATION_LIMIT = 128
    DEFAULT_DRAW_SAMPLE_COUNT = 64
    ROOT_CANDIDATE_BOOTSTRAP_SECONDS = 0.75

    def __init__(self, *, evaluator: LiveHandDecisionEvaluator | None = None, action_generator: CardSelector | None = None, draw_outcomes: PublicDrawOutcomeModel | None = None, play_width: int = 6, discard_width: int = 4, child_play_width: int | None = None, child_discard_width: int | None = None, horizon: int = 2, max_nodes: int | None = None, deadline: float | None = None):
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
        self.draw_outcomes = draw_outcomes or PublicDrawOutcomeModel(exact_combination_limit=self.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT, sample_count=self.DEFAULT_DRAW_SAMPLE_COUNT)
        self.discard_joker_projector = LiveDiscardJokerProjector()
        self.play_width = int(play_width)
        self.discard_width = int(discard_width)
        self.child_play_width = int(play_width if child_play_width is None else child_play_width)
        self.child_discard_width = int(discard_width if child_discard_width is None else child_discard_width)
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
        estimates = [self._estimate_action(state, action, self.horizon) for action in candidates]
        best = max(estimates, key=self._estimate_key)
        return LiveBlindPlan(best.action, best.value, self.horizon, best.exact, len(candidates))

    def _check_deadline(self) -> None:
        if self.deadline is not None and perf_counter() >= self.deadline:
            raise PlannerSearchBudgetExceeded("live blind planner search exceeded wall-clock budget")

    def _consume_node(self) -> None:
        self._check_deadline()
        if self.max_nodes is not None and self.nodes_evaluated >= self.max_nodes:
            raise PlannerSearchBudgetExceeded(f"live blind planner search exceeded node budget ({self.max_nodes})")
        self.nodes_evaluated += 1

    def _best_value(self, state, depth: int) -> tuple[LiveBlindPlanValue, bool]:
        if self._is_cleared(state):
            return self._terminal_value(state, clear=True), True
        if int(getattr(state, "hands_remaining", 0)) <= 0 or depth <= 0:
            return self._terminal_value(state, clear=False), True
        candidates = self._candidate_actions(state, allow_discards=depth > 1, play_width=self.child_play_width, discard_width=self.child_discard_width)
        if not candidates:
            return self._terminal_value(state, clear=False), True
        estimates = [self._estimate_action(state, action, depth) for action in candidates]
        best = max(estimates, key=self._estimate_key)
        return best.value, best.exact

    def _estimate_action(self, state, action: BalatroAction, depth: int) -> _ActionEstimate:
        self._consume_node()
        if action.name == PLAY_CARDS:
            previous = getattr(self, "_round_end_play_action", None)
            self._round_end_play_action = action
            try:
                return self._estimate_play(state, action, depth)
            finally:
                if previous is None:
                    self.__dict__.pop("_round_end_play_action", None)
                else:
                    self._round_end_play_action = previous
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
        projected_state = projection.state_after_scoring or deepcopy(state)
        if depth <= 1:
            for score_outcome in projection.outcomes:
                score_after = int(getattr(state, "score", 0)) + score_outcome.score
                outcome_state = self._score_outcome_state(score_outcome, projected_state)
                branch_state = deepcopy(outcome_state)
                branch_state.score = score_after
                branch_state.hands_remaining = hands_after
                value = self._terminal_value(branch_state, clear=(target > 0 and score_after >= target))
                total_value = total_value.plus(value.weighted(score_outcome.probability))
            return _ActionEstimate(action, total_value, exact)
        retained_cards = [card for index, card in enumerate(projected_state.hand) if index not in played_indices]
        joker_drawn_cards = max(0, len(getattr(projected_state, "hand", [])) - len(getattr(state, "hand", [])))
        replacement_draw_count = max(0, len(action.cards) - joker_drawn_cards)
        composition = None
        draw_distribution = None
        for score_outcome in projection.outcomes:
            outcome_state = self._score_outcome_state(score_outcome, projected_state)
            score_after = int(getattr(state, "score", 0)) + score_outcome.score
            if target > 0 and score_after >= target:
                branch_state = deepcopy(outcome_state); branch_state.score = score_after; branch_state.hands_remaining = hands_after
                total_value = total_value.plus(self._terminal_value(branch_state, clear=True).weighted(score_outcome.probability)); continue
            if hands_after <= 0:
                branch_state = deepcopy(outcome_state); branch_state.score = score_after; branch_state.hands_remaining = 0
                total_value = total_value.plus(self._terminal_value(branch_state, clear=False).weighted(score_outcome.probability)); continue
            retained_state = deepcopy(outcome_state); retained_state.score = score_after; retained_state.hands_remaining = hands_after; retained_state.hand = list(retained_cards)
            guaranteed_value = self._guaranteed_next_play_value(retained_state)
            if guaranteed_value is not None:
                total_value = total_value.plus(guaranteed_value.weighted(score_outcome.probability)); continue
            if replacement_draw_count <= 0:
                value, child_exact = self._best_value(retained_state, depth - 1); exact = exact and child_exact
                total_value = total_value.plus(value.weighted(score_outcome.probability)); continue
            if draw_distribution is None:
                composition = PublicDeckComposition.from_state(state)
                draw_distribution = self.draw_outcomes.distribution(composition, replacement_draw_count)
                exact = exact and draw_distribution.exact
            for draw_outcome in draw_distribution.outcomes:
                next_state = deepcopy(outcome_state); next_state.score = score_after; next_state.hands_remaining = hands_after
                next_state.hand = list(retained_cards) + [self.draw_outcomes.card_from_signature(signature) for signature in draw_outcome.cards]
                next_state.deck = self.draw_outcomes.remaining_cards(composition, draw_outcome)
                value, child_exact = self._best_value(next_state, depth - 1); exact = exact and child_exact
                total_value = total_value.plus(value.weighted(score_outcome.probability * draw_outcome.probability))
        return _ActionEstimate(action, total_value, exact)

    def _guaranteed_next_play_value(self, state) -> LiveBlindPlanValue | None:
        candidates = self._candidate_actions(state, allow_discards=False, play_width=self.child_play_width, discard_width=0)
        if not candidates:
            return None
        estimates = [self._estimate_action(state, action, 1) for action in candidates]
        guaranteed = [estimate for estimate in estimates if estimate.exact and estimate.value.clear_probability >= 1.0 - 1e-12]
        if not guaranteed:
            return None
        return max(guaranteed, key=lambda estimate: self._value_key(estimate.value)).value

    def _estimate_discard(self, state, action: BalatroAction, depth: int) -> _ActionEstimate:
        if int(getattr(state, "discards_remaining", 0)) <= 0:
            return _ActionEstimate(action, LiveBlindPlanValue(-1.0, 0.0, 0.0, 0.0, 0.0), True)
        discard_state = self.discard_joker_projector.project(state, action.cards)
        discards_after = max(0, int(state.discards_remaining) - 1)
        if depth <= 1:
            next_state = deepcopy(discard_state); next_state.discards_remaining = discards_after
            return _ActionEstimate(action, self._terminal_value(next_state, clear=False), True)
        composition = PublicDeckComposition.from_state(state)
        draw_distribution = self.draw_outcomes.distribution(composition, len(action.cards))
        removed_indices = self._card_indices(state.hand, action.cards)
        total_value = self._zero_value(); exact = draw_distribution.exact
        for draw_outcome in draw_distribution.outcomes:
            next_state = deepcopy(discard_state); next_state.discards_remaining = discards_after
            kept = [card for index, card in enumerate(next_state.hand) if index not in removed_indices]
            next_state.hand = kept + [self.draw_outcomes.card_from_signature(signature) for signature in draw_outcome.cards]
            next_state.deck = self.draw_outcomes.remaining_cards(composition, draw_outcome)
            value, child_exact = self._best_value(next_state, depth - 1); exact = exact and child_exact
            total_value = total_value.plus(value.weighted(draw_outcome.probability))
        return _ActionEstimate(action, total_value, exact)

    def _rank_actions_with_deadline(self, state, actions, *, priority, limit: int, soft_deadline: float | None = None) -> list[BalatroAction]:
        scored = []
        for action in actions:
            self._check_deadline()
            if soft_deadline is not None and scored and perf_counter() >= soft_deadline: break
            score = priority(state, action); self._check_deadline(); scored.append((score, action))
            if soft_deadline is not None and perf_counter() >= soft_deadline: break
        scored.sort(key=lambda item: item[0], reverse=True)
        return [action for _, action in scored[:limit]]

    def _candidate_actions(self, state, *, allow_discards: bool, play_width: int | None = None, discard_width: int | None = None) -> list[BalatroAction]:
        play_limit = self.play_width if play_width is None else int(play_width); discard_limit = self.discard_width if discard_width is None else int(discard_width); root = play_width is None and discard_width is None
        initial_root = int(getattr(self, "nodes_evaluated", 0)) == 0; soft_deadline = None
        if initial_root:
            soft_deadline = perf_counter() + self.ROOT_CANDIDATE_BOOTSTRAP_SECONDS
            if self.deadline is not None: soft_deadline = min(self.deadline, soft_deadline)
        self._check_deadline(); plays = self.action_generator.generate_play_actions(state); self._check_deadline()
        plays = self._prefilter_plays(state, plays, limit=_ROOT_PLAY_PREFILTER if root else _CHILD_PLAY_PREFILTER, soft_deadline=soft_deadline if initial_root else None)
        ranked_plays = self._rank_plays_with_short_reserve(state, plays, limit=play_limit, soft_deadline=soft_deadline)
        if initial_root and soft_deadline is not None and perf_counter() >= soft_deadline:
            return self._ensure_root_discard_reserve(state, ranked_plays, allow_discards=allow_discards, discard_limit=discard_limit)
        if not allow_discards or discard_limit <= 0 or int(getattr(state, "discards_remaining", 0)) <= 0: return ranked_plays
        self._check_deadline(); discards = self.action_generator.generate_discard_actions(state); self._check_deadline()
        discards = self._prefilter_discards(state, discards, limit=_ROOT_DISCARD_PREFILTER if root else _CHILD_DISCARD_PREFILTER, soft_deadline=soft_deadline if initial_root else None)
        ranked_discards = self._rank_actions_with_deadline(state, discards, priority=self._discard_priority, limit=discard_limit, soft_deadline=soft_deadline if initial_root else None)
        return self._ensure_root_discard_reserve(state, ranked_plays + ranked_discards, allow_discards=allow_discards, discard_limit=discard_limit)

    def _prefilter_plays(self, state, actions, *, limit: int, soft_deadline: float | None = None):
        values = list(actions)
        if len(values) <= limit: return values
        records = []
        for action in values:
            self._check_deadline()
            if self._soft_deadline_reached(soft_deadline, work_started=bool(records)): break
            hand = self._cheap_hand(state, action); key = self._cheap_play_key_from_hand(action, hand); self._check_deadline(); records.append((action, hand, key))
            if self._soft_deadline_reached(soft_deadline, work_started=True): break
        if not records: return values[:limit]
        ranked_records = sorted(records, key=lambda item: item[2], reverse=True); selected = [action for action, _, _ in ranked_records[:limit]]; selected_ids = {id(action) for action in selected}; representatives = []
        for hand in _HAND_STRENGTH:
            if hand == PokerHand.HIGH_CARD: continue
            candidates = [record for record in records if record[1] == hand]
            if not candidates: continue
            representative, _, _ = min(candidates, key=lambda item: (len(getattr(item[0], "cards", ()) or ()), -item[2][2], -item[2][1]))
            if id(representative) not in selected_ids: representatives.append(representative)
        if not representatives: return selected
        keep = max(0, limit - len(representatives)); return selected[:keep] + representatives[:limit]

    def _prefilter_discards(self, state, actions, *, limit: int, soft_deadline: float | None = None):
        values = list(actions)
        if len(values) <= limit: return values
        records = []
        for action in values:
            self._check_deadline()
            if self._soft_deadline_reached(soft_deadline, work_started=bool(records)): break
            key = self._cheap_discard_key(state, action); self._check_deadline(); records.append((action, key))
            if self._soft_deadline_reached(soft_deadline, work_started=True): break
        if not records: return values[:limit]
        ranked_records = sorted(records, key=lambda item: item[1], reverse=True); reserve = min(_WIDE_DISCARD_RESERVE, max(0, int(limit)))
        if reserve <= 0: return []
        widest_records = sorted(records, key=lambda item: (len(getattr(item[0], "cards", ()) or ()), item[1][0]), reverse=True)[:reserve]
        widest_ids = {id(action) for action, _ in widest_records}; primary = [action for action, _ in ranked_records if id(action) not in widest_ids]; widest = [action for action, _ in widest_records]
        return primary[: max(0, limit - len(widest))] + widest

    def _rank_plays_with_short_reserve(self, state, plays, *, limit: int, soft_deadline: float | None = None):
        if limit <= 0: return []
        priority = self._play_priority if soft_deadline is None else self._cheap_play_key
        ranked = self._rank_actions_with_deadline(state, plays, priority=priority, limit=limit, soft_deadline=soft_deadline)
        if len(plays) <= max(limit * 2, 12) or self._soft_deadline_reached(soft_deadline, work_started=bool(ranked)): return ranked
        reserve = min(_SHORT_PLAY_RESERVE, limit)
        if reserve <= 0: return ranked
        short_records = []
        for action in plays:
            self._check_deadline()
            if self._soft_deadline_reached(soft_deadline, work_started=bool(short_records)): break
            if len(getattr(action, "cards", ()) or ()) > 2: continue
            key = self._cheap_play_key(state, action); self._check_deadline()
            if key[0] > _HAND_STRENGTH[PokerHand.HIGH_CARD]: short_records.append((action, key))
            if self._soft_deadline_reached(soft_deadline, work_started=True): break
        if not short_records: return ranked
        short_ranked = [action for action, _ in sorted(short_records, key=lambda item: item[1], reverse=True)[:reserve]]; selected_ids = {id(action) for action in ranked}; additions = [action for action in short_ranked if id(action) not in selected_ids]
        if not additions: return ranked
        return ranked[: max(0, limit - len(additions))] + additions

    def _projection_free_discard_reserve(self, state, actions, *, limit: int):
        values = list(actions)
        if limit <= 0 or not values: return []
        records = []
        for action in values:
            if records and self.deadline is not None and perf_counter() >= self.deadline: break
            try: key = self._cheap_discard_key(state, action)
            except (AttributeError, TypeError, ValueError, RuntimeError): key = (0.0, len(getattr(action, "cards", ()) or ()))
            records.append((action, key))
            if self.deadline is not None and perf_counter() >= self.deadline: break
        if not records: return values[:limit]
        ranked = sorted(records, key=lambda item: item[1], reverse=True); widest = max(records, key=lambda item: (len(getattr(item[0], "cards", ()) or ()), item[1]))[0]; selected = [action for action, _ in ranked[:limit]]
        if widest not in selected: selected = selected[: max(0, limit - 1)] + [widest]
        return selected[:limit]

    def _ensure_root_discard_reserve(self, state, candidates, *, allow_discards: bool, discard_limit: int):
        values = list(candidates)
        if int(getattr(self, "nodes_evaluated", 0) or 0) != 0 or not allow_discards or discard_limit <= 0 or int(getattr(state, "discards_remaining", 0) or 0) <= 0 or _active_hook(state) or any(getattr(action, "name", None) == DISCARD_CARDS for action in values): return values
        if self.deadline is not None and perf_counter() >= self.deadline: return values
        generate_discards = getattr(self.action_generator, "generate_discard_actions", None)
        if not callable(generate_discards): return values
        try: legal_discards = list(generate_discards(state))
        except (AttributeError, TypeError, ValueError, RuntimeError): return values
        if not legal_discards: return values
        reserve = self._projection_free_discard_reserve(state, legal_discards, limit=min(_ROOT_DISCARD_RESERVE, discard_limit)); return values + reserve

    @staticmethod
    def _soft_deadline_reached(soft_deadline: float | None, *, work_started: bool) -> bool:
        return bool(work_started and soft_deadline is not None and perf_counter() >= soft_deadline)

    @staticmethod
    def _cheap_hand(state, action) -> PokerHand:
        try: return HandEvaluator().evaluate(list(getattr(action, "cards", ()) or ()), rules=hand_rules_for_state(state))
        except (AttributeError, TypeError, ValueError): return PokerHand.HIGH_CARD

    @staticmethod
    def _cheap_play_key_from_hand(action, hand: PokerHand) -> tuple[int, int, int, int]:
        cards = list(getattr(action, "cards", ()) or ()); rank_sum = 0; enhanced = 0
        for card in cards:
            rank_sum += _RANK_VALUES.get(str(getattr(card, "rank", "")).upper(), 0)
            if any(getattr(card, field, None) for field in ("enhancement", "edition", "seal")): enhanced += 1
        return (_HAND_STRENGTH.get(hand, 0), enhanced, rank_sum, -len(cards))

    @classmethod
    def _cheap_play_key(cls, state, action): return cls._cheap_play_key_from_hand(action, cls._cheap_hand(state, action))

    @staticmethod
    def _cheap_discard_key(state, action):
        cards = list(getattr(action, "cards", ()) or ()); removed = {id(card) for card in cards}; kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
        try: promise = LiveBlindClearPlanner().evaluator._retained_structure_value(kept)
        except (AttributeError, TypeError, ValueError): promise = 0.0
        return float(promise), len(cards)

    def _root_play_priority(self, state, action):
        ensure_cache = getattr(self.evaluator, "_ensure_outer_d1_cache", None); action_key = getattr(self.evaluator, "_action_key", None); projection_cache = getattr(self.evaluator, "_outer_d1_projection_cache", None)
        if callable(ensure_cache) and callable(action_key):
            ensure_cache(state)
            if isinstance(projection_cache, dict):
                cached = projection_cache.get(action_key(action))
                if cached is not None: return (float(cached.clear_probability), float(cached.expected_hand_score), int(cached.hand_score), -len(action.cards))
        hand_for_cards = getattr(self.evaluator, "_hand_for_cards", None); scorer = getattr(self.evaluator, "scorer", None)
        if not callable(hand_for_cards) or scorer is None: return (0.0, float(len(action.cards)), len(action.cards), -len(action.cards))
        hand = hand_for_cards(state, action.cards); base = scorer.SCORES[hand]; scoring_cards = scorer.scoring_cards(hand, list(action.cards or []), rules=hand_rules_for_state(state)); card_chips = sum(scorer.card_chip_value(card) for card in scoring_cards if not scorer.is_card_debuffed(card)); literal_score = float((base.chips + card_chips) * base.mult * base.x_mult); remaining = max(0, self._target(state) - int(getattr(state, "score", 0) or 0)); literal_clear = 1.0 if remaining > 0 and literal_score >= remaining else 0.0
        return (literal_clear, literal_score, int(base.chips * base.mult), -len(action.cards))

    def _play_priority(self, state, action):
        projection = self.evaluator.project_play(state, action); selected_gold = sum(1 for card in action.cards if self._active_gold(card))
        return (projection.clear_probability, projection.expected_hand_score, projection.hand_score, -len(action.cards), -selected_gold)

    def _discard_priority(self, state, action): return float(self.evaluator.evaluate(state, action)), len(action.cards)

    def _terminal_value(self, state, *, clear: bool):
        target = self._target(state); score = float(getattr(state, "score", 0)); effective_clear = bool(clear or self._mr_bones_rescues(state)); progress = min(1.0, max(0.0, score / target)) if target > 0 else 0.0; generated = self._held_round_end_consumables(state) if effective_clear else 0
        return LiveBlindPlanValue(1.0 if effective_clear else 0.0, 1.0 if effective_clear else progress, score, float(getattr(state, "hands_remaining", 0)), float(getattr(state, "discards_remaining", 0)), float(len(getattr(state, "consumables", ()) or ())) + float(generated))

    def _held_round_end_consumables(self, state):
        action = getattr(self, "_round_end_play_action", None)
        if action is None: return 0
        slots = max(0, int(getattr(state, "consumable_slots", 0) or 0)); held_consumables = len(tuple(getattr(state, "consumables", ()) or ())); room = max(0, slots - held_consumables)
        if room <= 0: return 0
        held_cards = self._remaining_after_play(getattr(state, "hand", ()), getattr(action, "cards", ())); blue = sum(1 for card in held_cards if self._active_blue(card)); return min(room, blue)

    @staticmethod
    def _same_card(left, right):
        left_id = getattr(left, "live_id", None); right_id = getattr(right, "live_id", None)
        if left_id is not None or right_id is not None: return left_id is not None and left_id == right_id
        return left == right

    @classmethod
    def _remaining_after_play(cls, hand, selected):
        remaining = list(hand or ())
        for selected_card in tuple(selected or ()):
            for index, candidate in enumerate(remaining):
                if cls._same_card(candidate, selected_card): del remaining[index]; break
        return remaining

    @staticmethod
    def _active_gold(card): return str(getattr(card, "enhancement", "") or "") == "Gold" and not bool(getattr(card, "debuffed", False))

    @staticmethod
    def _active_blue(card): return str(getattr(card, "seal", "") or "") == "Blue" and not bool(getattr(card, "debuffed", False))

    @staticmethod
    def _zero_value(): return LiveBlindPlanValue(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    @staticmethod
    def _score_outcome_state(score_outcome, fallback_state): return fallback_state if getattr(score_outcome, "state_after_scoring", None) is None else score_outcome.state_after_scoring

    @staticmethod
    def _card_indices(hand, selected):
        selected_ids = {id(card) for card in selected}; return {index for index, card in enumerate(hand) if id(card) in selected_ids}

    @staticmethod
    def _kept_cards(hand, removed):
        removed_ids = {id(card) for card in removed}; return [card for card in hand if id(card) not in removed_ids]

    @staticmethod
    def _target(state): return int(getattr(getattr(state, "blind", None), "requirement", 0))

    def _is_cleared(self, state):
        target = self._target(state); return target > 0 and int(getattr(state, "score", 0)) >= target

    def _mr_bones_rescues(self, state):
        if int(getattr(state, "hands_remaining", 0) or 0) > 0: return False
        target = self._target(state); score = int(getattr(state, "score", 0) or 0)
        if target <= 0 or score >= target or score * 4 < target: return False
        return any(type(joker).__name__ == "MrBonesJoker" for joker in getattr(state, "jokers", []))

    @classmethod
    def _estimate_key(cls, estimate):
        value = estimate.value
        action_name = getattr(estimate.action, "name", None)
        if estimate.exact and float(value.clear_probability) >= 1.0 - _EPSILON and float(value.expected_progress) >= 1.0 - _EPSILON and action_name == PLAY_CARDS:
            return (value.clear_probability, 1, value.expected_progress, value.expected_hands_remaining, value.expected_discards_remaining, -len(getattr(estimate.action, "cards", ()) or ()), value.expected_score)
        if action_name == DISCARD_CARDS and float(value.clear_probability) < 1.0 - _EPSILON:
            return (value.clear_probability, 0, value.expected_progress, value.expected_hands_remaining, value.expected_discards_remaining, value.expected_score, 1 if bool(estimate.exact) else 0, value.expected_consumables)
        canonical = (value.clear_probability, 1 if estimate.exact else 0, value.expected_progress, value.expected_hands_remaining, value.expected_discards_remaining, value.expected_score, value.expected_consumables)
        return (*canonical[:-1], 0, canonical[-1])

    @staticmethod
    def _value_key(value): return (value.clear_probability, value.expected_progress, value.expected_hands_remaining, value.expected_discards_remaining, value.expected_score, value.expected_consumables)

    @staticmethod
    def _require_state(state):
        if getattr(state, "phase", None) != "SELECTING_HAND": raise ValueError("live blind-clear planning requires SELECTING_HAND phase")
        if not getattr(state, "hand", None): raise ValueError("live blind-clear planning requires a visible hand")
        if int(getattr(state, "hands_remaining", 0)) <= 0: raise ValueError("live blind-clear planning requires at least one hand")
