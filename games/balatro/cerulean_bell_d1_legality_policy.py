from __future__ import annotations

"""Final D1 legality guard for Cerulean Bell forced-card selection.

Cerulean Bell's public ``forced_selection`` card must belong to every Play or
Discard action. The core D1 planner already applies the shared boss legality
predicate to Play candidates, but root/recursive Discard candidate construction
can bypass that filter. Install a final candidate-list guard so both action types
obey the same authoritative boss mechanic without inventing any score utility.
"""

from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner


def install_cerulean_bell_d1_legality_policy() -> None:
    if getattr(D1LiveBlindClearPlanner, "_cerulean_legality_installed", False):
        return

    original_candidate_actions = D1LiveBlindClearPlanner._candidate_actions

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

    D1LiveBlindClearPlanner._candidate_actions = candidate_actions
    D1LiveBlindClearPlanner._cerulean_legality_installed = True
