from __future__ import annotations

from itertools import combinations

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import PACE_RECOVERY


_MAX_SELECTED_CARDS = 5

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


def _direct_play_actions(state) -> list[BalatroAction]:
    hand = list(getattr(state, "hand", ()) or ())
    actions: list[BalatroAction] = []
    for amount in range(1, min(_MAX_SELECTED_CARDS, len(hand)) + 1):
        for cards in combinations(hand, amount):
            actions.append(BalatroAction(PLAY_CARDS, cards=list(cards)))
    return actions


def _normalized_hand_name(value) -> str:
    return str(value or "").strip().upper().replace(" ", "_")


def _hand_type(state, action: BalatroAction) -> PokerHand:
    try:
        return HandEvaluator().evaluate(
            list(getattr(action, "cards", ()) or ()),
            rules=hand_rules_for_state(state),
        )
    except (AttributeError, TypeError, ValueError):
        return PokerHand.HIGH_CARD


def _play_key(state, action: BalatroAction) -> tuple[int, int, int]:
    hand = _hand_type(state, action)
    ranks = sum(
        _RANK_VALUES.get(str(getattr(card, "rank", "") or "").upper(), 0)
        for card in tuple(getattr(action, "cards", ()) or ())
    )
    return (
        _HAND_STRENGTH.get(hand, 0),
        ranks,
        -len(tuple(getattr(action, "cards", ()) or ())),
    )


def _mouth_locked_hand(state) -> str | None:
    if str(getattr(state, "boss_name", "") or "") != "The Mouth":
        return None
    if boss_blind_disabled_by_owned_jokers(state):
        return None
    forced = getattr(state, "boss_blind_only_hand", None)
    normalized = _normalized_hand_name(forced)
    return normalized or None


def _retained_forced_structure(engine, state, action: BalatroAction, forced: str) -> float:
    removed = {id(card) for card in tuple(getattr(action, "cards", ()) or ())}
    kept = [
        card
        for card in tuple(getattr(state, "hand", ()) or ())
        if id(card) not in removed
    ]
    structure_fit = getattr(getattr(engine, "policy", None), "_structure_fit", None)
    if not callable(structure_fit):
        return 0.0
    try:
        return float(structure_fit(kept, forced, rules=hand_rules_for_state(state)))
    except TypeError:
        return float(structure_fit(kept, forced))
    except (AttributeError, ValueError, RuntimeError):
        return 0.0


def _bounded_discard_candidates(engine, state) -> tuple[list[BalatroAction], object | None]:
    """Return legal structural discards only through existing bounded authorities."""
    if int(getattr(state, "discards_remaining", 0) or 0) <= 0:
        return [], None
    planner = getattr(engine, "planner", None)
    action_generator = getattr(planner, "action_generator", None)
    generate_discards = getattr(action_generator, "generate_discard_actions", None)
    retained_value = getattr(
        getattr(getattr(engine, "policy", None), "evaluator", None),
        "_retained_structure_value",
        None,
    )
    if not callable(generate_discards) or not callable(retained_value):
        return [], None
    try:
        return list(generate_discards(state)), retained_value
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return [], None


def _ordinary_discard_key(state, action: BalatroAction, retained_value) -> tuple[float, int]:
    removed = {id(card) for card in tuple(getattr(action, "cards", ()) or ())}
    kept = [
        card
        for card in tuple(getattr(state, "hand", ()) or ())
        if id(card) not in removed
    ]
    try:
        value = float(retained_value(kept))
    except (AttributeError, TypeError, ValueError, RuntimeError):
        value = 0.0
    return value, len(tuple(getattr(action, "cards", ()) or ()))


def _select_structural_timeout_action(engine, state):
    """Choose bounded structural recovery without Joker-aware projection work.

    Plays are enumerated directly from the visible hand. A discard may be selected
    only when the production planner exposes its legal discard generator and the
    production policy exposes the retained-structure evaluator. This preserves the
    historical timeout contract: timeout can use bounded structural discard evidence
    but cannot fabricate a discard in compatibility/minimal states where those
    authorities are unavailable.
    """
    plays = _direct_play_actions(state)
    if not plays:
        planner = getattr(engine, "planner", None)
        child_candidates = getattr(planner, "_child_play_candidates", None)
        if callable(child_candidates):
            plays = list(
                child_candidates(
                    state,
                    max(1, int(getattr(planner, "play_width", 1) or 1)),
                )
            )
    if not plays:
        raise RuntimeError("D1 timeout fallback found no legal Play action")

    forced = _mouth_locked_hand(state)
    discards, retained_value = _bounded_discard_candidates(engine, state)
    hands_remaining = max(0, int(getattr(state, "hands_remaining", 0) or 0))

    if forced is not None:
        matching = [
            action
            for action in plays
            if _normalized_hand_name(_hand_type(state, action).value) == forced
        ]
        if matching:
            best_play = max(matching, key=lambda action: _play_key(state, action))
            return best_play, best_play, "Play", len(plays)

        if discards:
            action = max(
                discards,
                key=lambda candidate: (
                    _retained_forced_structure(engine, state, candidate, forced),
                    _ordinary_discard_key(state, candidate, retained_value),
                ),
            )
            best_play = max(plays, key=lambda action: _play_key(state, action))
            return action, best_play, "Discard", len(plays)

        if int(getattr(state, "discards_remaining", 0) or 0) <= 0:
            records = [
                (
                    action,
                    _retained_forced_structure(engine, state, action, forced),
                    len(tuple(getattr(action, "cards", ()) or ())),
                )
                for action in plays
            ]
            best_structure = max(structure for _, structure, _ in records)
            structural = [
                record
                for record in records
                if record[1] + 1e-12 >= best_structure
            ]
            best_width = max(width for _, _, width in structural)
            action = max(
                (candidate for candidate, _, width in structural if width == best_width),
                key=lambda candidate: _play_key(state, candidate),
            )
            return action, action, "Play", len(plays)

        best_play = max(plays, key=lambda action: _play_key(state, action))
        return best_play, best_play, "Play", len(plays)

    best_play = max(plays, key=lambda action: _play_key(state, action))
    action = best_play
    selected_kind = "Play"
    best_hand_rank = _play_key(state, best_play)[0]
    if hands_remaining > 1 and best_hand_rank <= _HAND_STRENGTH[PokerHand.PAIR] and discards:
        action = max(
            discards,
            key=lambda candidate: _ordinary_discard_key(state, candidate, retained_value),
        )
        selected_kind = "Discard"

    return action, best_play, selected_kind, len(plays)


def _bounded_structural_timeout_fallback(
    self,
    state,
    *,
    search_attempts,
):
    """Return cheap structural recovery after the D1 wall-clock budget expires."""
    self.planner._require_state(state)
    action, best_play, selected_kind, play_count = _select_structural_timeout_action(self, state)

    discards_remaining = max(0, int(getattr(state, "discards_remaining", 0) or 0))
    hands_remaining = max(0, int(getattr(state, "hands_remaining", 0) or 0))
    target = float(getattr(getattr(state, "blind", None), "requirement", 0) or 0)
    score = float(getattr(state, "score", 0) or 0)
    progress = min(1.0, max(0.0, score / target)) if target > 0 else 0.0

    def structural_value(candidate):
        return LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=progress,
            expected_score=score,
            expected_hands_remaining=float(
                max(0, hands_remaining - (candidate.name == PLAY_CARDS))
            ),
            expected_discards_remaining=float(
                max(0, discards_remaining - (candidate.name == DISCARD_CARDS))
            ),
        )

    plan = LiveBlindPlan(
        action=action,
        value=structural_value(action),
        horizon=1,
        exact=False,
        candidate_count=play_count,
    )
    best_play_plan = (
        plan
        if action is best_play
        else LiveBlindPlan(
            action=best_play,
            value=structural_value(best_play),
            horizon=1,
            exact=False,
            candidate_count=play_count,
        )
    )
    forced = _mouth_locked_hand(state)
    rationale = [
        "D1 wall-clock budget exhausted before pace fallback completed",
        f"selected a projection-free structural {selected_kind} without further Joker-aware projection",
        "structural discard is permitted only through the existing legal discard generator and retained-structure evaluator",
    ]
    if forced is not None:
        rationale.append(
            f"The Mouth is locked to {forced}; timeout recovery applies the forced-hand constraint before ordinary structural ranking"
        )
    rationale.append("take only this action, then re-observe and replan")

    return self.policy._decision(
        mode=PACE_RECOVERY,
        selected=plan,
        best_play=best_play_plan,
        best_discard=plan if action.name == DISCARD_CARDS else None,
        pace_target=self.policy._pace_target(state),
        best_play_immediate_score=0.0,
        best_play_pace_ratio=0.0,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=None,
        clear_path_candidates=0,
        sampled_clear_path_confirmed=False,
        setup_discard_consensus=False,
        confidence=0.25,
        rationale=tuple(rationale),
        plans=(plan,),
        search_attempts=tuple(search_attempts),
    )
