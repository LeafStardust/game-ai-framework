from __future__ import annotations

"""Final D1 legality and future-selection authority for Cerulean Bell.

Cerulean Bell's public ``forced_selection`` card must belong to every Play or
Discard action. The core D1 planner already applies the shared boss legality
predicate to Play candidates, but root/recursive Discard candidate construction
can bypass that filter. Install a final candidate-list guard so both action types
obey the same authoritative boss mechanic without inventing any score utility.

After a real Play/Discard the selected card has necessarily left the hand. Balatro
then forces one random card in the newly visible hand. Recursive D1 therefore
branches uniformly over every possible next forced card before evaluating the
child state instead of treating the future Bell state as unconstrained/incomplete.
"""

from copy import deepcopy

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner


def _cerulean_future_forced_branches(state):
    """Return exact equiprobable next forced-card states, or ``None`` if inactive."""
    if state is None:
        return None
    if str(getattr(state, "boss_name", "") or "") != "Cerulean Bell":
        return None
    if boss_blind_disabled_by_owned_jokers(state):
        return None

    hand = list(getattr(state, "hand", ()) or ())
    if not hand:
        return None

    # At authoritative checkpoints the observer has already hydrated the Bell's
    # current forced card. Do not re-roll it. This brancher is only for a newly
    # drawn hypothetical hand that has not yet received the next Bell selection.
    if any(bool(getattr(card, "forced_selection", False)) for card in hand):
        return None

    probability = 1.0 / len(hand)
    branches = []
    for selected_index in range(len(hand)):
        branch = deepcopy(state)
        for index, card in enumerate(branch.hand):
            card.forced_selection = index == selected_index
        branches.append((probability, branch))
    return tuple(branches)


def install_cerulean_bell_d1_legality_policy() -> None:
    if getattr(D1LiveBlindClearPlanner, "_cerulean_legality_installed", False):
        return

    original_candidate_actions = D1LiveBlindClearPlanner._candidate_actions
    original_best_value = D1LiveBlindClearPlanner._best_value

    def candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        actions = original_candidate_actions(
            self,
            state,
            allow_discards=allow_discards,
            play_width=play_width,
            discard_width=discard_width,
        )
        return [
            action
            for action in actions
            if boss_play_action_is_legal(state, action)
        ]

    def best_value(self, state, depth: int):
        branches = _cerulean_future_forced_branches(state)
        if not branches:
            return original_best_value(self, state, depth)

        total = self._zero_value()
        exact = True
        for probability, branch_state in branches:
            value, branch_exact = original_best_value(self, branch_state, depth)
            total = total.plus(value.weighted(probability))
            exact = exact and branch_exact
        return total, exact

    D1LiveBlindClearPlanner._candidate_actions = candidate_actions
    D1LiveBlindClearPlanner._best_value = best_value
    D1LiveBlindClearPlanner._cerulean_legality_installed = True
