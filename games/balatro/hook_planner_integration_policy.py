from __future__ import annotations

from copy import deepcopy

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner, _ActionEstimate
from games.balatro.live.draw_model import PublicDeckComposition


def _hook_active(state) -> bool:
    return (
        state is not None
        and str(getattr(state, "boss_name", "") or "") == "The Hook"
        and not boss_blind_disabled_by_owned_jokers(state)
    )


def _same_card(left, right) -> bool:
    left_id = getattr(left, "live_id", None)
    right_id = getattr(right, "live_id", None)
    if left_id is not None or right_id is not None:
        return left_id is not None and left_id == right_id
    return left == right


def _remove_selected_cards(source, selected) -> list:
    remaining = list(source or [])
    for selected_card in list(selected or []):
        for index, candidate in enumerate(remaining):
            if _same_card(candidate, selected_card):
                del remaining[index]
                break
    return remaining


def install_hook_planner_integration_policy() -> None:
    """Keep Hook forced-discard score branches exact on the reusable base planner."""
    if getattr(LiveBlindClearPlanner, "_hook_planner_integration_installed", False):
        return

    original_estimate_play = LiveBlindClearPlanner._estimate_play

    def estimate_play(self, state, action, depth):
        if not _hook_active(state) or depth <= 1:
            return original_estimate_play(self, state, action, depth)

        projection = self.evaluator.project_play(state, action)
        total_value = self._zero_value()
        exact = projection.joker_projection_complete
        hands_after = max(0, int(getattr(state, "hands_remaining", 0)) - 1)
        target = self._target(state)
        fallback_state = projection.state_after_scoring
        if fallback_state is None:
            fallback_state = state
        composition = PublicDeckComposition.from_state(state)
        original_hand_size = len(list(getattr(state, "hand", ()) or ()))

        for score_outcome in projection.outcomes:
            outcome_state = self._score_outcome_state(score_outcome, fallback_state)
            score_after = int(getattr(state, "score", 0)) + score_outcome.score

            if target > 0 and score_after >= target:
                branch_state = deepcopy(outcome_state)
                branch_state.score = score_after
                branch_state.hands_remaining = hands_after
                total_value = total_value.plus(
                    self._terminal_value(branch_state, clear=True).weighted(
                        score_outcome.probability
                    )
                )
                continue

            if hands_after <= 0:
                branch_state = deepcopy(outcome_state)
                branch_state.score = score_after
                branch_state.hands_remaining = 0
                total_value = total_value.plus(
                    self._terminal_value(branch_state, clear=False).weighted(
                        score_outcome.probability
                    )
                )
                continue

            retained_cards = _remove_selected_cards(
                getattr(outcome_state, "hand", ()),
                action.cards,
            )
            retained_state = deepcopy(outcome_state)
            retained_state.score = score_after
            retained_state.hands_remaining = hands_after
            retained_state.hand = list(retained_cards)

            guaranteed_value = self._guaranteed_next_play_value(retained_state)
            if guaranteed_value is not None:
                total_value = total_value.plus(
                    guaranteed_value.weighted(score_outcome.probability)
                )
                continue

            replacement_draw_count = max(
                0,
                original_hand_size - len(retained_cards),
            )
            if replacement_draw_count <= 0:
                value, child_exact = self._best_value(retained_state, depth - 1)
                exact = exact and child_exact
                total_value = total_value.plus(
                    value.weighted(score_outcome.probability)
                )
                continue

            draw_distribution = self.draw_outcomes.distribution(
                composition,
                replacement_draw_count,
            )
            exact = exact and draw_distribution.exact
            for draw_outcome in draw_distribution.outcomes:
                next_state = deepcopy(outcome_state)
                next_state.score = score_after
                next_state.hands_remaining = hands_after
                next_state.hand = list(retained_cards) + [
                    self.draw_outcomes.card_from_signature(signature)
                    for signature in draw_outcome.cards
                ]
                next_state.deck = self.draw_outcomes.remaining_cards(
                    composition,
                    draw_outcome,
                )
                value, child_exact = self._best_value(next_state, depth - 1)
                exact = exact and child_exact
                probability = score_outcome.probability * draw_outcome.probability
                total_value = total_value.plus(value.weighted(probability))

        return _ActionEstimate(action, total_value, exact)

    LiveBlindClearPlanner._estimate_play = estimate_play
    LiveBlindClearPlanner._hook_planner_integration_installed = True
