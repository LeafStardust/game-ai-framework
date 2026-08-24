from __future__ import annotations

"""Corrections derived from authoritative live batch 20260824T075105Z.

The batch exposed three structural defects:
- broad scenario-derived rank requirements could connect a hand-payoff Joker to most
  rank-density feature nodes, manufacturing a fake mega-strategy;
- direct no-discard mechanics such as Green Joker were not protected until the
  canonical no_discard Bond had already matured;
- D1 root ranking projected every playable subset before the first search node,
  allowing one pathological projection to dominate wall-clock latency.

This layer corrects those defects without changing the Phase-A calibration values.
"""

from games.balatro.bonds import behavior_strategy
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro import d1_candidate_deadline_policy as deadline_policy
from games.balatro import latest_batch_no_discard_policy as no_discard_policy


_MAX_CONCRETE_RANK_REQUIREMENTS = 5
_ROOT_PLAY_PREFILTER = 18
_CHILD_PLAY_PREFILTER = 12
_ROOT_DISCARD_PREFILTER = 14
_CHILD_DISCARD_PREFILTER = 8

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


def install_latest_075105_correction_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_latest_075105_correction_installed", False):
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
        plays = _prefilter(
            plays,
            limit=_ROOT_PLAY_PREFILTER if root else _CHILD_PLAY_PREFILTER,
            key=_cheap_play_key,
        )
        ranked_plays = deadline_policy._rank_with_deadline(
            self,
            state,
            plays,
            key=self._play_priority,
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

    LiveBlindClearPlanner._candidate_actions = candidate_actions_bounded
    LiveBlindClearPlanner._latest_075105_correction_installed = True
