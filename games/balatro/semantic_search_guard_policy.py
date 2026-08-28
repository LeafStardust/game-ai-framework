from __future__ import annotations

"""Semantic relationship and bounded D1 candidate-search guards.

Production evidence exposed structural defects retained by this layer:
- broad scenario-derived rank requirements could connect a hand-payoff Joker to most
  rank-density feature nodes, manufacturing a fake mega-strategy;
- D1 root ranking projected every playable subset before the first search node,
  allowing one pathological projection to dominate wall-clock latency;
- semantic candidate prefiltering itself could repeatedly classify every playable
  subset across every hand family without observing the planner deadline;
- retained-structure-only discard prefiltering could fill the narrow projected beam
  with singleton discards, hiding materially better multi-card redraws from the
  full-blind planner;
- non-clearing sampled discard recovery could lose to singleton redraws solely
  because the singleton outcome space was cheap enough to enumerate exactly;
- when bounded search has zero modeled progress for every discard, retained/local
  value alone can repeatedly peel one card instead of taking a meaningful redraw.

No-discard execution semantics now live as ordinary canonical D1 evidence and are
intentionally not patched from this search/runtime module.
"""

from time import perf_counter

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds import behavior_strategy
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


_MAX_CONCRETE_RANK_REQUIREMENTS = 5
_ROOT_PLAY_PREFILTER = 64
_CHILD_PLAY_PREFILTER = 24
_ROOT_DISCARD_PREFILTER = 14
_CHILD_DISCARD_PREFILTER = 8
_SHORT_PLAY_RESERVE = 2
_WIDE_DISCARD_RESERVE = 2
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


def _is_feature_rank_node(node) -> bool:
    return str(getattr(node, "source", "")).lower().startswith("feature:rank:")


def _rank_requirement_count(node) -> int:
    features = (
        set(getattr(node, "requires", ()) or ())
        | set(getattr(node, "scales_with", ()) or ())
        | set(getattr(node, "amplifies", ()) or ())
    )
    return sum(1 for feature in features if "rank:" in str(feature).lower())


def _cheap_hand(state, action) -> PokerHand:
    try:
        return HandEvaluator().evaluate(
            list(getattr(action, "cards", ()) or ()),
            rules=hand_rules_for_state(state),
        )
    except (AttributeError, TypeError, ValueError):
        return PokerHand.HIGH_CARD


def _cheap_play_key_from_hand(action, hand: PokerHand) -> tuple[int, int, int, int]:
    cards = list(getattr(action, "cards", ()) or ())
    rank_sum = 0
    enhanced = 0
    for card in cards:
        rank_sum += _RANK_VALUES.get(str(getattr(card, "rank", "")).upper(), 0)
        if any(getattr(card, field, None) for field in ("enhancement", "edition", "seal")):
            enhanced += 1
    return (_HAND_STRENGTH.get(hand, 0), enhanced, rank_sum, -len(cards))


def _cheap_play_key(state, action) -> tuple[int, int, int, int]:
    return _cheap_play_key_from_hand(action, _cheap_hand(state, action))


def _cheap_discard_key(state, action) -> tuple[float, int]:
    cards = list(getattr(action, "cards", ()) or ())
    removed = {id(card) for card in cards}
    kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
    try:
        promise = LiveBlindClearPlanner().evaluator._retained_structure_value(kept)
    except (AttributeError, TypeError, ValueError):
        promise = 0.0
    return float(promise), len(cards)


def _soft_deadline_reached(soft_deadline: float | None, *, work_started: bool) -> bool:
    return bool(
        work_started
        and soft_deadline is not None
        and perf_counter() >= soft_deadline
    )


def _prefilter(actions, *, limit: int, key):
    values = list(actions)
    if len(values) <= limit:
        return values
    return sorted(values, key=key, reverse=True)[:limit]


def _prefilter_discards(
    planner,
    state,
    actions,
    *,
    limit: int,
    soft_deadline: float | None = None,
):
    values = list(actions)
    if len(values) <= limit:
        return values

    records: list[tuple[object, tuple[float, int]]] = []
    for action in values:
        planner._check_deadline()
        if _soft_deadline_reached(soft_deadline, work_started=bool(records)):
            break
        key = _cheap_discard_key(state, action)
        planner._check_deadline()
        records.append((action, key))
        if _soft_deadline_reached(soft_deadline, work_started=True):
            break

    if not records:
        return values[:limit]

    ranked_records = sorted(records, key=lambda item: item[1], reverse=True)
    reserve = min(_WIDE_DISCARD_RESERVE, max(0, int(limit)))
    if reserve <= 0:
        return []

    widest_records = sorted(
        records,
        key=lambda item: (
            len(getattr(item[0], "cards", ()) or ()),
            item[1][0],
        ),
        reverse=True,
    )[:reserve]
    widest_ids = {id(action) for action, _ in widest_records}
    primary = [action for action, _ in ranked_records if id(action) not in widest_ids]
    widest = [action for action, _ in widest_records]
    return primary[: max(0, limit - len(widest))] + widest


def _prefilter_plays(
    planner,
    state,
    actions,
    *,
    limit: int,
    soft_deadline: float | None = None,
):
    values = list(actions)
    if len(values) <= limit:
        return values

    records: list[tuple[object, PokerHand, tuple[int, int, int, int]]] = []
    for action in values:
        planner._check_deadline()
        if _soft_deadline_reached(soft_deadline, work_started=bool(records)):
            break
        hand = _cheap_hand(state, action)
        key = _cheap_play_key_from_hand(action, hand)
        planner._check_deadline()
        records.append((action, hand, key))
        if _soft_deadline_reached(soft_deadline, work_started=True):
            break

    if not records:
        return values[:limit]

    ranked_records = sorted(records, key=lambda item: item[2], reverse=True)
    selected_records = ranked_records[:limit]
    selected = [action for action, _, _ in selected_records]
    selected_ids = {id(action) for action in selected}

    representatives: list = []
    for hand in _HAND_STRENGTH:
        if hand == PokerHand.HIGH_CARD:
            continue
        candidates = [record for record in records if record[1] == hand]
        if not candidates:
            continue
        representative, _, _ = min(
            candidates,
            key=lambda item: (
                len(getattr(item[0], "cards", ()) or ()),
                -item[2][2],
                -item[2][1],
            ),
        )
        if id(representative) not in selected_ids:
            representatives.append(representative)

    if not representatives:
        return selected
    keep = max(0, limit - len(representatives))
    return selected[:keep] + representatives[:limit]


def _rank_plays_with_short_reserve(
    self,
    state,
    plays,
    *,
    limit: int,
    soft_deadline: float | None = None,
):
    if limit <= 0:
        return []
    # Initial-root candidate shaping must stay projection-free. The selected beam is
    # still evaluated by the canonical Joker-aware planner immediately afterwards;
    # calling project_play here merely duplicates that work and one stochastic Joker
    # projection can exceed the entire D1 wall-clock budget before node 1 exists.
    priority = self._play_priority if soft_deadline is None else _cheap_play_key
    ranked = self._rank_actions_with_deadline(
        state,
        plays,
        priority=priority,
        limit=limit,
        soft_deadline=soft_deadline,
    )
    if len(plays) <= max(limit * 2, 12):
        return ranked
    if _soft_deadline_reached(soft_deadline, work_started=bool(ranked)):
        return ranked

    reserve = min(_SHORT_PLAY_RESERVE, limit)
    if reserve <= 0:
        return ranked

    short_records: list[tuple[object, tuple[int, int, int, int]]] = []
    for action in plays:
        self._check_deadline()
        if _soft_deadline_reached(soft_deadline, work_started=bool(short_records)):
            break
        if len(getattr(action, "cards", ()) or ()) > 2:
            continue
        key = _cheap_play_key(state, action)
        self._check_deadline()
        if key[0] > _HAND_STRENGTH[PokerHand.HIGH_CARD]:
            short_records.append((action, key))
        if _soft_deadline_reached(soft_deadline, work_started=True):
            break

    if not short_records:
        return ranked

    short_ranked = [
        action
        for action, _ in sorted(short_records, key=lambda item: item[1], reverse=True)[:reserve]
    ]
    selected_ids = {id(action) for action in ranked}
    additions = [action for action in short_ranked if id(action) not in selected_ids]
    if not additions:
        return ranked
    return ranked[: max(0, limit - len(additions))] + additions


def _nonclearing_discard_quality_key(plan) -> tuple[float, float, float, float, float, int]:
    """Rank discard recovery quality before exact-enumeration status."""
    value = plan.value
    return (
        float(value.clear_probability),
        float(value.expected_progress),
        float(value.expected_hands_remaining),
        float(value.expected_discards_remaining),
        float(value.expected_score),
        1 if bool(plan.exact) else 0,
    )


def _zero_signal_discard(plan) -> bool:
    """True when bounded D1 search has no modeled outcome signal for a discard."""
    if getattr(plan.action, "name", None) != DISCARD_CARDS:
        return False
    value = plan.value
    return (
        float(value.clear_probability) <= _EPSILON
        and float(value.expected_progress) <= _EPSILON
        and float(value.expected_score) <= _EPSILON
    )


def _zero_signal_discard_tiebreak(plan, *, strategy_fit: float = 0.0) -> tuple[float, int]:
    """Preserve real strategy intent, then prefer a meaningful redraw over peeling."""
    return (
        float(strategy_fit),
        len(getattr(plan.action, "cards", ()) or ()),
    )


def install_semantic_search_guard_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_semantic_search_guard_installed", False):
        return

    original_relation = behavior_strategy._relation

    def relation(left, right):
        if _is_feature_rank_node(left) and _rank_requirement_count(right) > _MAX_CONCRETE_RANK_REQUIREMENTS:
            return None
        if _is_feature_rank_node(right) and _rank_requirement_count(left) > _MAX_CONCRETE_RANK_REQUIREMENTS:
            return None
        return original_relation(left, right)

    behavior_strategy._relation = relation

    def candidate_actions_bounded(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        play_limit = self.play_width if play_width is None else int(play_width)
        discard_limit = self.discard_width if discard_width is None else int(discard_width)
        root = play_width is None and discard_width is None

        initial_root = int(getattr(self, "nodes_evaluated", 0)) == 0
        soft_deadline = None
        if initial_root:
            soft_deadline = perf_counter() + self.ROOT_CANDIDATE_BOOTSTRAP_SECONDS
            if self.deadline is not None:
                soft_deadline = min(self.deadline, soft_deadline)

        self._check_deadline()
        plays = self.action_generator.generate_play_actions(state)
        self._check_deadline()
        plays = _prefilter_plays(
            self,
            state,
            plays,
            limit=_ROOT_PLAY_PREFILTER if root else _CHILD_PLAY_PREFILTER,
            soft_deadline=soft_deadline if initial_root else None,
        )
        ranked_plays = _rank_plays_with_short_reserve(
            self,
            state,
            plays,
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
        discards = _prefilter_discards(
            self,
            state,
            discards,
            limit=_ROOT_DISCARD_PREFILTER if root else _CHILD_DISCARD_PREFILTER,
            soft_deadline=soft_deadline if initial_root else None,
        )
        ranked_discards = self._rank_actions_with_deadline(
            state,
            discards,
            priority=self._discard_priority,
            limit=discard_limit,
            soft_deadline=soft_deadline if initial_root else None,
        )
        return ranked_plays + ranked_discards

    original_estimate_key = LiveBlindClearPlanner._estimate_key

    def estimate_key(cls, estimate):
        value = estimate.value
        action_name = getattr(estimate.action, "name", None)
        if (
            estimate.exact
            and float(value.clear_probability) >= 1.0 - _EPSILON
            and float(value.expected_progress) >= 1.0 - _EPSILON
            and action_name == PLAY_CARDS
        ):
            return (
                value.clear_probability,
                1,
                value.expected_progress,
                value.expected_hands_remaining,
                value.expected_discards_remaining,
                -len(getattr(estimate.action, "cards", ()) or ()),
                value.expected_score,
            )
        if (
            action_name == DISCARD_CARDS
            and float(value.clear_probability) < 1.0 - _EPSILON
        ):
            return (
                value.clear_probability,
                0,
                value.expected_progress,
                value.expected_hands_remaining,
                value.expected_discards_remaining,
                value.expected_score,
                1 if bool(estimate.exact) else 0,
                value.expected_consumables,
            )
        canonical = original_estimate_key(estimate)
        return (*canonical[:-1], 0, canonical[-1])

    original_strategy_key = StrategyAwareLiveHandActionPolicy._within_type_key

    def strategy_within_type_key(self, plan):
        if (
            getattr(plan.action, "name", None) == DISCARD_CARDS
            and float(plan.value.clear_probability) < 1.0 - _EPSILON
        ):
            quality = _nonclearing_discard_quality_key(plan)
            original = original_strategy_key(self, plan)
            if _zero_signal_discard(plan):
                strategy_fit = 0.0
                state = getattr(self, "_ranking_state", None)
                if state is not None:
                    try:
                        strategy_fit = float(self._strategy_fit(state, plan.action)[0])
                    except (AttributeError, TypeError, ValueError, RuntimeError):
                        strategy_fit = 0.0
                return (
                    *quality,
                    *_zero_signal_discard_tiebreak(plan, strategy_fit=strategy_fit),
                    original,
                )
            return (*quality, original)
        return original_strategy_key(self, plan)

    LiveBlindClearPlanner._candidate_actions = candidate_actions_bounded
    LiveBlindClearPlanner._estimate_key = classmethod(estimate_key)
    StrategyAwareLiveHandActionPolicy._within_type_key = strategy_within_type_key
    LiveBlindClearPlanner._semantic_search_guard_installed = True
