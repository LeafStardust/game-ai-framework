from __future__ import annotations

from itertools import combinations
from time import perf_counter

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.blind_clear_planner import (
    LiveBlindPlan,
    LiveBlindPlanValue,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.hand_action_policy import (
    PACE_RECOVERY,
    LiveHandActionDecisionEngine,
)


BOOTSTRAP_MAX_SECONDS = 1.50
BOOTSTRAP_BUDGET_FRACTION = 0.25
BOOTSTRAP_MIN_TOTAL_BUDGET_SECONDS = 0.05
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


def _select_structural_timeout_play(engine, state):
    """Choose a projection-free emergency Play without inventing new discard evidence."""
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
    if forced is not None:
        matching = [
            action
            for action in plays
            if _normalized_hand_name(_hand_type(state, action).value) == forced
        ]
        if matching:
            best_play = max(matching, key=lambda action: _play_key(state, action))
            return best_play, len(plays)

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
            return max(
                (candidate for candidate, _, width in structural if width == best_width),
                key=lambda candidate: _play_key(state, candidate),
            ), len(plays)

    return max(plays, key=lambda action: _play_key(state, action)), len(plays)


def _bounded_structural_timeout_fallback(
    self,
    state,
    *,
    search_attempts,
):
    """Return a cheap Play-only emergency action after the D1 wall-clock budget expires."""
    self.planner._require_state(state)
    action, play_count = _select_structural_timeout_play(self, state)

    discards_remaining = max(0, int(getattr(state, "discards_remaining", 0) or 0))
    hands_remaining = max(0, int(getattr(state, "hands_remaining", 0) or 0))
    target = float(getattr(getattr(state, "blind", None), "requirement", 0) or 0)
    score = float(getattr(state, "score", 0) or 0)
    progress = min(1.0, max(0.0, score / target)) if target > 0 else 0.0

    value = LiveBlindPlanValue(
        clear_probability=0.0,
        expected_progress=progress,
        expected_score=score,
        expected_hands_remaining=float(max(0, hands_remaining - 1)),
        expected_discards_remaining=float(discards_remaining),
    )
    plan = LiveBlindPlan(
        action=action,
        value=value,
        horizon=1,
        exact=False,
        candidate_count=play_count,
    )
    forced = _mouth_locked_hand(state)
    rationale = [
        "D1 wall-clock budget exhausted before pace fallback completed",
        "selected a projection-free structural Play without fabricating discard evidence",
        "timeout recovery does not call Joker-aware projection machinery",
    ]
    if forced is not None:
        rationale.append(
            f"The Mouth is locked to {forced}; emergency fallback uses a matching Play when one is directly available"
        )
    rationale.append("take only this action, then re-observe and replan")

    return self.policy._decision(
        mode=PACE_RECOVERY,
        selected=plan,
        best_play=plan,
        best_discard=None,
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


def install_safe_pace_timeout_patch() -> None:
    if getattr(LiveHandActionDecisionEngine, "_safe_pace_timeout_installed", False):
        return

    original_decide = LiveHandActionDecisionEngine.decide

    def decide(self, state):
        configured_budget = getattr(self, "max_search_seconds", None)
        if configured_budget is not None and float(configured_budget) > 0.0:
            configured_budget = float(configured_budget)

            if configured_budget <= BOOTSTRAP_MIN_TOTAL_BUDGET_SECONDS:
                return original_decide(self, state)

            started = perf_counter()
            bootstrap_budget = min(
                BOOTSTRAP_MAX_SECONDS,
                configured_budget * BOOTSTRAP_BUDGET_FRACTION,
            )
            self._search_deadline = started + bootstrap_budget
            try:
                bootstrap_plans = self._rank_immediate_plans(state)
            except (PlannerSearchBudgetExceeded, AttributeError, RuntimeError, TypeError, ValueError):
                bootstrap_plans = []

            if bootstrap_plans and hasattr(self, "_adaptive_plan_history"):
                self._adaptive_plan_history.append(tuple(bootstrap_plans))

            elapsed = max(0.0, perf_counter() - started)
            remaining = configured_budget - elapsed
            if remaining <= 0.0:
                return self._structural_timeout_fallback(
                    state,
                    search_attempts=(),
                )

            self.max_search_seconds = remaining
            try:
                return original_decide(self, state)
            finally:
                self.max_search_seconds = configured_budget

        return original_decide(self, state)

    LiveHandActionDecisionEngine.decide = decide
    LiveHandActionDecisionEngine._structural_timeout_fallback = _bounded_structural_timeout_fallback
    LiveHandActionDecisionEngine._safe_pace_timeout_installed = True
