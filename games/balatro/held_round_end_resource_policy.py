from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner, _ActionEstimate
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner


def _same_card(left, right) -> bool:
    left_id = getattr(left, "live_id", None)
    right_id = getattr(right, "live_id", None)
    if left_id is not None or right_id is not None:
        return left_id is not None and left_id == right_id
    return left == right


def _remaining_after_play(hand, selected) -> list:
    remaining = list(hand or ())
    for selected_card in tuple(selected or ()):
        for index, candidate in enumerate(remaining):
            if _same_card(candidate, selected_card):
                del remaining[index]
                break
    return remaining


def _active_gold(card) -> bool:
    return (
        str(getattr(card, "enhancement", "") or "") == "Gold"
        and not bool(getattr(card, "debuffed", False))
    )


def _active_blue(card) -> bool:
    return (
        str(getattr(card, "seal", "") or "") == "Blue"
        and not bool(getattr(card, "debuffed", False))
    )


def _blue_reward_count(state, held_cards) -> int:
    slots = max(0, int(getattr(state, "consumable_slots", 0) or 0))
    held_consumables = len(tuple(getattr(state, "consumables", ()) or ()))
    room = max(0, slots - held_consumables)
    if room <= 0:
        return 0
    blue = sum(1 for card in held_cards if _active_blue(card))
    return min(room, blue)


def _clears_after_outcome(
    planner,
    state,
    score_after: int,
    hands_after: int,
    outcome_state,
) -> bool:
    target = planner._target(state)
    if target > 0 and score_after >= target:
        return True
    if hands_after > 0:
        return False
    branch_state = outcome_state
    branch_state.score = score_after
    branch_state.hands_remaining = hands_after
    return bool(planner._mr_bones_rescues(branch_state))


def _gold_aware_priority(original_priority):
    def play_priority(self, state, action):
        base = original_priority(self, state, action)
        selected_gold = sum(1 for card in action.cards if _active_gold(card))
        # Existing mechanical score/clear ordering stays first. This final field
        # only determines stable ordering when those values are identical; max()
        # over equal expectimax values therefore keeps the Gold-preserving action.
        return (*tuple(base), -selected_gold)

    return play_priority


def install_held_round_end_resource_policy() -> None:
    """Preserve literal held-card round-end rewards on survival-equivalent D1 lines.

    Steel already belongs to literal hand scoring and therefore needs no extra
    authority here. Blue Seal is different: its Planet is created only when the
    round ends with the card held and consumable capacity exists. Carry that exact
    generated-consumable count into the existing late D1 resource tie-break.

    Gold cards pay cash only at round end. D1 has no common unit that can compare
    dollars against Planets without inventing utility, so Gold is used only as the
    final deterministic ordering tie-break between otherwise equal play candidates.
    It never outranks clear probability, score, hands, discards, or any expectimax
    value component.
    """
    if getattr(
        LiveBlindClearPlanner,
        "_held_round_end_resource_policy_installed",
        False,
    ):
        return

    original_estimate_play = LiveBlindClearPlanner._estimate_play
    original_live_priority = LiveBlindClearPlanner._play_priority
    original_d1_priority = D1LiveBlindClearPlanner._play_priority

    def estimate_play(self, state, action, depth):
        estimate = original_estimate_play(self, state, action, depth)

        projection = self.evaluator.project_play(state, action)
        hands_after = max(0, int(getattr(state, "hands_remaining", 0)) - 1)
        expected_blue_rewards = 0.0
        fallback_state = projection.state_after_scoring
        if fallback_state is None:
            fallback_state = state

        for outcome in projection.outcomes:
            outcome_state = self._score_outcome_state(outcome, fallback_state)
            score_after = int(getattr(state, "score", 0)) + int(outcome.score)
            branch_state = deepcopy(outcome_state)
            if not _clears_after_outcome(
                self,
                state,
                score_after,
                hands_after,
                branch_state,
            ):
                continue
            held_cards = _remaining_after_play(
                getattr(outcome_state, "hand", ()),
                action.cards,
            )
            expected_blue_rewards += (
                float(outcome.probability)
                * float(_blue_reward_count(outcome_state, held_cards))
            )

        if expected_blue_rewards <= 0.0:
            return estimate

        value = replace(
            estimate.value,
            expected_consumables=(
                float(estimate.value.expected_consumables)
                + expected_blue_rewards
            ),
        )
        return _ActionEstimate(estimate.action, value, estimate.exact)

    LiveBlindClearPlanner._estimate_play = estimate_play
    LiveBlindClearPlanner._play_priority = _gold_aware_priority(original_live_priority)
    D1LiveBlindClearPlanner._play_priority = _gold_aware_priority(original_d1_priority)
    LiveBlindClearPlanner._held_round_end_resource_policy_installed = True
