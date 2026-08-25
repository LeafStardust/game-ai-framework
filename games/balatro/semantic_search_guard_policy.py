from __future__ import annotations

"""Semantic relationship and bounded D1 candidate-search guards.

Production evidence exposed three structural defects:
- broad scenario-derived rank requirements could connect a hand-payoff Joker to most
  rank-density feature nodes, manufacturing a fake mega-strategy;
- direct no-discard mechanics such as Green Joker were not protected until the
  canonical no_discard Bond had already matured;
- D1 root ranking projected every playable subset before the first search node,
  allowing one pathological projection to dominate wall-clock latency.

This layer corrects those defects without changing the Phase-A calibration values.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.bonds import behavior_strategy
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro import d1_candidate_deadline_policy as deadline_policy
from games.balatro import strategy_execution_guard_policy as no_discard_policy


_MAX_CONCRETE_RANK_REQUIREMENTS = 5
# Keep root projection bounded, but retain enough visible plays that exact-clear
# low-card-count lines such as a retained Pair are not erased by a cheap
# hand-category prefilter before the real scorer can evaluate them.
_ROOT_PLAY_PREFILTER = 64
_CHILD_PLAY_PREFILTER = 24
_ROOT_DISCARD_PREFILTER = 14
_CHILD_DISCARD_PREFILTER = 8
_SHORT_PLAY_RESERVE = 2

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


def _cheap_play_key(action) -> tuple[int, int, int, int]:
    cards = list(getattr(action, "cards", ()) or ())
    try:
        hand = HandEvaluator().evaluate(cards)
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
        if any(
            getattr(card, field, None)
            for field in ("enhancement", "edition", "seal")
        ):
            enhanced += 1
    return (
        _HAND_STRENGTH.get(hand, 0),
        enhanced,
        rank_sum,
        -len(cards),
    )


def _cheap_hand(action) -> PokerHand:
    try:
        return HandEvaluator().evaluate(list(getattr(action, "cards", ()) or ()))
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


def _prefilter_plays(actions, *, limit: int):
    """Bound cheap root/child play candidates without erasing compact made hands.

    Large hands can contain many 4/5-card supersets that classify as Pair/Two Pair
    and therefore outrank the literal 2-card Pair on the cheap rank-sum key. Those
    supersets must not consume every prefilter slot: a compact made hand can retain
    another already-made hand and prove an exact multi-hand clear without consulting
    redraws. Preserve one minimal-card representative per made hand class, then fill
    the remaining bounded budget with the ordinary cheap ordering.
    """
    values = list(actions)
    if len(values) <= limit:
        return values

    ranked = sorted(values, key=_cheap_play_key, reverse=True)
    selected = ranked[:limit]
    selected_ids = {id(action) for action in selected}

    representatives: list = []
    for hand in _HAND_STRENGTH:
        if hand == PokerHand.HIGH_CARD:
            continue
        candidates = [action for action in values if _cheap_hand(action) == hand]
        if not candidates:
            continue
        representative = min(
            candidates,
            key=lambda action: (
                len(getattr(action, "cards", ()) or ()),
                -_cheap_play_key(action)[2],
                -_cheap_play_key(action)[1],
            ),
        )
        if id(representative) not in selected_ids:
            representatives.append(representative)

    if not representatives:
        return selected

    # Replace only the cheap tail. The prefilter size remains strictly bounded.
    keep = max(0, limit - len(representatives))
    return selected[:keep] + representatives[:limit]


def _rank_plays_with_short_reserve(self, state, plays, *, limit: int, stage: str):
    """Keep strong short made hands available in large combinatorial beams.

    Small candidate sets preserve canonical projection ordering exactly. For large
    hands, the main beam is still ranked by full projection, but a tiny reserve is
    selected with the cheap deterministic hand classifier rather than projected
    immediate score. This preserves made Pair/Trips/etc. lines that can prove an
    exact retained-hand clear without adding another round of expensive projection.
    """
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
        and _cheap_play_key(action)[0] > _HAND_STRENGTH[PokerHand.HIGH_CARD]
    ]
    if not short or reserve <= 0:
        return ranked

    deadline_policy._check_deadline(self, f"{stage} short-play reserve")
    short_ranked = sorted(short, key=_cheap_play_key, reverse=True)[:reserve]
    deadline_policy._check_deadline(self, f"{stage} short-play reserve")

    selected_ids = {id(action) for action in ranked}
    additions = [action for action in short_ranked if id(action) not in selected_ids]
    if not additions:
        return ranked

    return ranked[: max(0, limit - len(additions))] + additions


def install_semantic_search_guard_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_semantic_search_guard_installed", False):
        return

    original_relation = behavior_strategy._relation

    def relation(left, right):
        # Scenario probing may discover that a Joker can score under many ordinary
        # card shapes. That must not be interpreted as the Joker *requiring* every
        # rank in the deck. A genuine rank-specific mechanic has a small concrete
        # requirement set (Walkie, Scholar, Fibonacci, Hack, etc.).
        if _is_feature_rank_node(left) and _rank_requirement_count(right) > _MAX_CONCRETE_RANK_REQUIREMENTS:
            return None
        if _is_feature_rank_node(right) and _rank_requirement_count(left) > _MAX_CONCRETE_RANK_REQUIREMENTS:
            return None
        return original_relation(left, right)

    behavior_strategy._relation = relation

    def direct_no_discard_engine(state) -> bool:
        owned = {
            no_discard_policy._joker_token(joker)
            for joker in tuple(getattr(state, "jokers", ()) or ())
        }
        # These mechanics lose value immediately on the first discard; waiting for
        # Bond maturity makes the execution contract arrive too late.
        if owned & {"greenjoker", "delayedgratificationjoker"}:
            return True
        # Banner is a softer round-level incentive: only elevate it to an execution
        # constraint once the canonical no_discard Bond agrees the build is using it.
        return "bannerjoker" in owned and no_discard_policy._realized_bond(state, "no_discard")

    no_discard_policy._realized_no_discard_engine = direct_no_discard_engine

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
        plays = _prefilter_plays(
            plays,
            limit=_ROOT_PLAY_PREFILTER if root else _CHILD_PLAY_PREFILTER,
        )
        ranked_plays = _rank_plays_with_short_reserve(
            self,
            state,
            plays,
            limit=play_limit,
            stage="play candidate ranking",
        )

        if (
            not allow_discards
            or discard_limit <= 0
            or int(getattr(state, "discards_remaining", 0)) <= 0
        ):
            return ranked_plays

        deadline_policy._check_deadline(self, "discard candidate generation")
        discards = self.action_generator.generate_discard_actions(state)
        deadline_policy._check_deadline(self, "discard candidate generation")
        discards = _prefilter(
            discards,
            limit=_ROOT_DISCARD_PREFILTER if root else _CHILD_DISCARD_PREFILTER,
            key=lambda action: _cheap_discard_key(state, action),
        )
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
        # Once an exact guaranteed clear is proven, surplus score above the blind
        # requirement has no survival value. Prefer consuming fewer played cards so
        # retained cards/resources remain available. For non-clearing/uncertain
        # lines, preserve the canonical estimate ordering exactly.
        if (
            estimate.exact
            and float(value.clear_probability) >= 1.0 - 1e-12
            and float(value.expected_progress) >= 1.0 - 1e-12
            and getattr(estimate.action, "name", None) == PLAY_CARDS
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
        canonical = original_estimate_key(estimate)
        return (*canonical[:-1], 0, canonical[-1])

    LiveBlindClearPlanner._candidate_actions = candidate_actions_bounded
    LiveBlindClearPlanner._estimate_key = classmethod(estimate_key)
    LiveBlindClearPlanner._semantic_search_guard_installed = True
