from __future__ import annotations

"""Semantic relationship and bounded D1 candidate-search guards.

Production evidence exposed structural defects retained by this layer:
- broad scenario-derived rank requirements could connect a hand-payoff Joker to most
  rank-density feature nodes, manufacturing a fake mega-strategy;
- D1 root ranking projected every playable subset before the first search node,
  allowing one pathological projection to dominate wall-clock latency;
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

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds import behavior_strategy
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro import d1_candidate_deadline_policy as deadline_policy


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


def _is_feature_rank_node(node) -> bool:
    return str(getattr(node, "source", "")).lower().startswith("feature:rank:")


def _rank_requirement_count(node) -> int:
    features = (
        set(getattr(node, "requires", ()) or ())
        | set(getattr(node, "scales_with", ()) or ())
        | set(getattr(node, "amplifies", ()) or ())
    )
    return sum(1 for feature in features if "rank:" in str(feature).lower())


def _cheap_play_key(state, action) -> tuple[int, int, int, int]:
    cards = list(getattr(action, "cards", ()) or ())
    try:
        hand = HandEvaluator().evaluate(cards, rules=hand_rules_for_state(state))
    except (AttributeError, TypeError, ValueError):
        hand = PokerHand.HIGH_CARD
    rank_sum = 0
    enhanced = 0
    rank_values = {
        "A": 14, "ACE": 14, "K": 13, "KING": 13, "Q": 12, "QUEEN": 12,
        "J": 11, "JACK": 11, "10": 10, "9": 9, "8": 8, "7": 7,
        "6": 6, "5": 5, "4": 4, "3": 3, "2": 2,
    }
    for card in cards:
        rank_sum += rank_values.get(str(getattr(card, "rank", "")).upper(), 0)
        if any(getattr(card, field, None) for field in ("enhancement", "edition", "seal")):
            enhanced += 1
    return (_HAND_STRENGTH.get(hand, 0), enhanced, rank_sum, -len(cards))


def _cheap_hand(state, action) -> PokerHand:
    try:
        return HandEvaluator().evaluate(
            list(getattr(action, "cards", ()) or ()),
            rules=hand_rules_for_state(state),
        )
    except (AttributeError, TypeError, ValueError):
        return PokerHand.HIGH_CARD


def _cheap_discard_key(state, action) -> tuple[float, int]:
    cards = list(getattr(action, "cards", ()) or ())
    removed = {id(card) for card in cards}
    kept = [card for card in getattr(state, "hand", ()) if id(card) not in removed]
    try:
        promise = LiveBlindClearPlanner().evaluator._retained_structure_value(kept)
    except (AttributeError, TypeError, ValueError):
        promise = 0.0
    return float(promise), len(cards)


def _prefilter(actions, *, limit: int, key):
    values = list(actions)
    if len(values) <= limit:
        return values
    return sorted(values, key=key, reverse=True)[:limit]


def _prefilter_discards(state, actions, *, limit: int):
    values = list(actions)
    if len(values) <= limit:
        return values

    ranked = sorted(values, key=lambda action: _cheap_discard_key(state, action), reverse=True)
    reserve = min(_WIDE_DISCARD_RESERVE, max(0, int(limit)))
    if reserve <= 0:
        return []

    widest = sorted(
        values,
        key=lambda action: (
            len(getattr(action, "cards", ()) or ()),
            _cheap_discard_key(state, action)[0],
        ),
        reverse=True,
    )[:reserve]
    widest_ids = {id(action) for action in widest}
    primary = [action for action in ranked if id(action) not in widest_ids]
    return primary[: max(0, limit - len(widest))] + widest


def _prefilter_plays(state, actions, *, limit: int):
    values = list(actions)
    if len(values) <= limit:
        return values

    ranked = sorted(values, key=lambda action: _cheap_play_key(state, action), reverse=True)
    selected = ranked[:limit]
    selected_ids = {id(action) for action in selected}

    representatives: list = []
    for hand in _HAND_STRENGTH:
        if hand == PokerHand.HIGH_CARD:
            continue
        candidates = [action for action in values if _cheap_hand(state, action) == hand]
        if not candidates:
            continue
        representative = min(
            candidates,
            key=lambda action: (
                len(getattr(action, "cards", ()) or ()),
                -_cheap_play_key(state, action)[2],
                -_cheap_play_key(state, action)[1],
            ),
        )
        if id(representative) not in selected_ids:
            representatives.append(representative)

    if not representatives:
        return selected
    keep = max(0, limit - len(representatives))
    return selected[:keep] + representatives[:limit]


def _rank_plays_with_short_reserve(self, state, plays, *, limit: int, stage: str):
    if limit <= 0:
        return []
    ranked = deadline_policy._rank_with_deadline(
        self,
        state,
        plays,
        key=self._play_priority,
        limit=limit,
        stage=stage,
    )
    if len(plays) <= max(limit * 2, 12):
        return ranked

    reserve = min(_SHORT_PLAY_RESERVE, limit)
    short = [
        action
        for action in plays
        if len(getattr(action, "cards", ()) or ()) <= 2
        and _cheap_play_key(state, action)[0] > _HAND_STRENGTH[PokerHand.HIGH_CARD]
    ]
    if not short or reserve <= 0:
        return ranked

    deadline_policy._check_deadline(self, f"{stage} short-play reserve")
    short_ranked = sorted(short, key=lambda action: _cheap_play_key(state, action), reverse=True)[:reserve]
    deadline_policy._check_deadline(self, f"{stage} short-play reserve")

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

        deadline_policy._check_deadline(self, "play candidate generation")
        plays = self.action_generator.generate_play_actions(state)
        deadline_policy._check_deadline(self, "play candidate generation")
        plays = _prefilter_plays(state, plays, limit=_ROOT_PLAY_PREFILTER if root else _CHILD_PLAY_PREFILTER)
        ranked_plays = _rank_plays_with_short_reserve(
            self,
            state,
            plays,
            limit=play_limit,
            stage="play candidate ranking",
        )

        if not allow_discards or discard_limit <= 0 or int(getattr(state, "discards_remaining", 0)) <= 0:
            return ranked_plays

        deadline_policy._check_deadline(self, "discard candidate generation")
        discards = self.action_generator.generate_discard_actions(state)
        deadline_policy._check_deadline(self, "discard candidate generation")
        discards = _prefilter_discards(state, discards, limit=_ROOT_DISCARD_PREFILTER if root else _CHILD_DISCARD_PREFILTER)
        ranked_discards = deadline_policy._rank_with_deadline(
            self,
            state,
            discards,
            key=self._discard_priority,
            limit=discard_limit,
            stage="discard candidate ranking",
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
