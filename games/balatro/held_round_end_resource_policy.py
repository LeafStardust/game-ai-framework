from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from games.balatro.hook_planner_integration_policy import install_hook_planner_integration_policy
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner, _ActionEstimate
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as CoreD1LiveBlindClearPlanner,
)
from games.balatro.serpent_draw_policy import install_serpent_draw_policy


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
        return (*tuple(base), -selected_gold)

    return play_priority


def _blue_aware_estimate(original_estimate_play):
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

    return estimate_play


def install_held_round_end_resource_policy() -> None:
    """Preserve literal held-card rewards on every reusable D1 planner surface."""
    if getattr(
        D1LiveBlindClearPlanner,
        "_held_round_end_resource_policy_installed",
        False,
    ):
        return

    # Base planner utilities remain part of the deterministic mechanics contract.
    # Install exact Hook/Serpent transition semantics before wrapping estimates so
    # held-resource projection composes with those boss mechanics rather than
    # bypassing them.
    install_serpent_draw_policy()
    install_hook_planner_integration_policy()

    original_live_estimate = LiveBlindClearPlanner._estimate_play
    original_core_estimate = CoreD1LiveBlindClearPlanner._estimate_play
    original_integrated_estimate = D1LiveBlindClearPlanner._estimate_play

    original_live_priority = LiveBlindClearPlanner._play_priority
    original_core_priority = CoreD1LiveBlindClearPlanner._play_priority
    original_integrated_priority = D1LiveBlindClearPlanner._play_priority

    LiveBlindClearPlanner._estimate_play = _blue_aware_estimate(original_live_estimate)
    CoreD1LiveBlindClearPlanner._estimate_play = _blue_aware_estimate(original_core_estimate)
    D1LiveBlindClearPlanner._estimate_play = _blue_aware_estimate(original_integrated_estimate)

    LiveBlindClearPlanner._play_priority = _gold_aware_priority(original_live_priority)
    CoreD1LiveBlindClearPlanner._play_priority = _gold_aware_priority(original_core_priority)
    D1LiveBlindClearPlanner._play_priority = _gold_aware_priority(original_integrated_priority)

    LiveBlindClearPlanner._held_round_end_resource_policy_installed = True
    CoreD1LiveBlindClearPlanner._held_round_end_resource_policy_installed = True
    D1LiveBlindClearPlanner._held_round_end_resource_policy_installed = True
