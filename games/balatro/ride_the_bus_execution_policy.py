from __future__ import annotations

"""Preserve accumulated Ride the Bus Mult on dominated terminal clear choices.

D1's bounded expectimax correctly carries Ride the Bus' persistent reset/increment
through non-terminal child states.  Once a play clears the blind immediately,
however, the terminal value intentionally stops at the current blind and may use
otherwise meaningless overkill score as a late tie-break.  A face-card clearing
play can therefore reset an accumulated Bus stack even when another currently
visible play also guarantees the clear with the same round resources.

This guard addresses only that dominated terminal case.  It never trades clear
probability, hands, discards, generated Blue-Seal consumables, or additional Gold
cards for Bus preservation.  Non-terminal and survival-sensitive choices remain
owned by ordinary D1 expectimax.
"""

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


_EPSILON = 1e-9
_FACE_RANKS = frozenset({"J", "Q", "K"})


def _active_bus_stack(state) -> int:
    values = []
    for joker in tuple(getattr(state, "jokers", ()) or ()):
        if type(joker).__name__ != "RideTheBusJoker":
            continue
        if bool(getattr(joker, "debuffed", False)):
            continue
        try:
            values.append(max(0, int(getattr(joker, "mult", 0) or 0)))
        except (TypeError, ValueError):
            continue
    return max(values, default=0)


def _scoring_has_face(state, action, evaluator: HandEvaluator) -> bool:
    cards = list(getattr(action, "cards", ()) or ())
    if not cards:
        return False
    rules = hand_rules_for_state(state)
    hand = evaluator.evaluate(cards, rules=rules)
    scoring = evaluator.scoring_cards(hand, cards, rules=rules)
    return any(str(getattr(card, "rank", "") or "") in _FACE_RANKS for card in scoring)


def _gold_sacrificed(action) -> int:
    return sum(
        1
        for card in tuple(getattr(action, "cards", ()) or ())
        if str(getattr(card, "enhancement", "") or "") == "Gold"
        and not bool(getattr(card, "debuffed", False))
    )


def _plan_metric(plan, name: str) -> float:
    try:
        return float(getattr(plan.value, name))
    except (AttributeError, TypeError, ValueError):
        return 0.0


def install_ride_the_bus_execution_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_ride_the_bus_terminal_preservation_installed",
        False,
    ):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide
    hand_evaluator = HandEvaluator()

    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        decision = original_decide(self, state, plans, **kwargs)
        stack = _active_bus_stack(state)
        if stack <= 0 or decision.action.name != PLAY_CARDS:
            return decision
        if not _scoring_has_face(state, decision.action, hand_evaluator):
            return decision

        selected_plan = getattr(decision, "selected_plan", None)
        if selected_plan is None:
            return decision
        try:
            selected_projection = self.evaluator.project_play(state, decision.action)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return decision
        if float(selected_projection.clear_probability) < 1.0 - _EPSILON:
            return decision

        selected_hands = _plan_metric(selected_plan, "expected_hands_remaining")
        selected_discards = _plan_metric(selected_plan, "expected_discards_remaining")
        selected_consumables = _plan_metric(selected_plan, "expected_consumables")
        selected_gold = _gold_sacrificed(decision.action)

        candidates = []
        for plan in plans:
            action = plan.action
            if action.name != PLAY_CARDS:
                continue
            if _scoring_has_face(state, action, hand_evaluator):
                continue
            try:
                projection = self.evaluator.project_play(state, action)
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            if float(projection.clear_probability) < 1.0 - _EPSILON:
                continue
            if _plan_metric(plan, "expected_hands_remaining") + _EPSILON < selected_hands:
                continue
            if _plan_metric(plan, "expected_discards_remaining") + _EPSILON < selected_discards:
                continue
            if _plan_metric(plan, "expected_consumables") + _EPSILON < selected_consumables:
                continue
            if _gold_sacrificed(action) > selected_gold:
                continue
            candidates.append((float(projection.expected_hand_score), plan))

        if not candidates:
            return decision

        _score, chosen = max(
            candidates,
            key=lambda item: (
                self._strategy_fit(state, item[1].action)[0],
                _plan_metric(item[1], "expected_consumables"),
                -_gold_sacrificed(item[1].action),
                item[0],
                self._within_type_key(item[1]),
            ),
        )
        if getattr(chosen.action, "cards", None) == getattr(decision.action, "cards", None):
            return decision

        projection = self.evaluator.project_play(state, chosen.action)
        pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
        pace_ratio = (
            float(projection.expected_hand_score) / pace_target
            if pace_target > 0.0
            else float("inf")
        )
        return replace(
            decision,
            action=chosen.action,
            selected_plan=chosen,
            selected_immediate_score=float(projection.expected_hand_score),
            selected_pace_ratio=pace_ratio,
            confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), 1.0),
            rationale=(
                "Ride the Bus terminal preservation: avoid resetting an accumulated stack for irrelevant overkill",
                f"current Ride the Bus Mult stack={stack}",
                "alternative play also guarantees the immediate blind clear",
                "alternative preserves at least the same hands, discards, Blue-Seal reward count, and Gold-card retention",
                "non-terminal/survival-sensitive face-card plays remain governed by ordinary D1 expectimax",
                *tuple(getattr(decision, "rationale", ()) or ()),
            ),
        )

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._ride_the_bus_terminal_preservation_installed = True
