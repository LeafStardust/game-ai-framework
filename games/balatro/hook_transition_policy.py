from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from math import comb

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner, _ActionEstimate
from games.balatro.live.draw_model import PublicDeckComposition


HOOK_DISCARD_COUNT = 2


def hook_active(state) -> bool:
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return False
    return str(getattr(state, "boss_name", "") or "") == "The Hook"


def install_hook_transition_policy() -> None:
    """Project The Hook's random forced discards inside D1 expectimax.

    Balatro discards up to two random cards from the cards left in hand after every
    played hand. Those are real discard events: discard-trigger Jokers and Purple
    Seals see them, but they do not consume one of the player's discard actions.
    The discarded cards are then replaced along with the cards that were played.

    The random selection is public uncertainty, so D1 branches uniformly over the
    possible retained-card subsets and then uses its ordinary unordered public draw
    distribution. This avoids both hidden draw order and a synthetic Hook penalty.
    """
    if getattr(LiveBlindClearPlanner, "_hook_transition_policy_installed", False):
        return

    original_estimate_play = LiveBlindClearPlanner._estimate_play

    def estimate_play(self, state, action, depth):
        if not hook_active(state) or depth <= 1:
            return original_estimate_play(self, state, action, depth)

        projection = self.evaluator.project_play(state, action)
        total_value = self._zero_value()
        exact = projection.joker_projection_complete
        hands_after = max(0, int(getattr(state, "hands_remaining", 0)) - 1)
        target = self._target(state)
        projected_state = projection.state_after_scoring
        if projected_state is None:
            projected_state = deepcopy(state)

        played_indices = self._card_indices(state.hand, action.cards)
        retained_template = [
            card
            for index, card in enumerate(projected_state.hand)
            if index not in played_indices
        ]
        joker_drawn_cards = max(
            0,
            len(getattr(projected_state, "hand", []))
            - len(getattr(state, "hand", [])),
        )
        ordinary_replacement_draws = max(0, len(action.cards) - joker_drawn_cards)
        composition = PublicDeckComposition.from_state(state)

        for score_outcome in projection.outcomes:
            outcome_state = self._score_outcome_state(score_outcome, projected_state)
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

            retained_count = len(retained_template)
            forced_count = min(HOOK_DISCARD_COUNT, retained_count)
            forced_sets = tuple(combinations(range(retained_count), forced_count))
            forced_probability = 1.0 / max(1, comb(retained_count, forced_count))

            for forced_indices in forced_sets or ((),):
                forced_index_set = set(forced_indices)
                hook_state = deepcopy(outcome_state)
                hook_state.score = score_after
                hook_state.hands_remaining = hands_after
                hook_state.hand = list(retained_template)
                forced_cards = [
                    hook_state.hand[index]
                    for index in forced_indices
                ]
                hook_state = self.discard_joker_projector.project(
                    hook_state,
                    forced_cards,
                    consume_discard_use=False,
                )
                kept_after_hook = [
                    card
                    for index, card in enumerate(hook_state.hand)
                    if index not in forced_index_set
                ]

                draw_count = ordinary_replacement_draws + forced_count
                draw_distribution = self.draw_outcomes.distribution(
                    composition,
                    draw_count,
                )
                exact = exact and draw_distribution.exact

                for draw_outcome in draw_distribution.outcomes:
                    next_state = deepcopy(hook_state)
                    next_state.hand = list(kept_after_hook) + [
                        self.draw_outcomes.card_from_signature(signature)
                        for signature in draw_outcome.cards
                    ]
                    next_state.deck = self.draw_outcomes.remaining_cards(
                        composition,
                        draw_outcome,
                    )
                    value, child_exact = self._best_value(next_state, depth - 1)
                    exact = exact and child_exact
                    probability = (
                        score_outcome.probability
                        * forced_probability
                        * draw_outcome.probability
                    )
                    total_value = total_value.plus(value.weighted(probability))

        return _ActionEstimate(action, total_value, exact)

    LiveBlindClearPlanner._estimate_play = estimate_play
    LiveBlindClearPlanner._hook_transition_policy_installed = True
