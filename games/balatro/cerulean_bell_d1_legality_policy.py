from __future__ import annotations

"""Cerulean Bell future forced-selection projection.

Current-checkpoint Play/Discard legality now lives directly in the canonical
``D1LiveBlindClearPlanner._candidate_actions`` path through the shared boss legality
predicate. This module retains only the future Bell mechanic that cannot be inferred
from the newly drawn hypothetical hand itself.

After a real Play/Discard the selected card has necessarily left the hand. Balatro
then forces one random card in the newly visible hand. Recursive D1 therefore
branches uniformly over every possible next forced card before evaluating the child
state instead of treating the future Bell state as unconstrained/incomplete.
"""

from copy import deepcopy

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
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
    if getattr(D1LiveBlindClearPlanner, "_cerulean_future_projection_installed", False):
        return

    original_best_value = D1LiveBlindClearPlanner._best_value

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

    D1LiveBlindClearPlanner._best_value = best_value
    D1LiveBlindClearPlanner._cerulean_future_projection_installed = True