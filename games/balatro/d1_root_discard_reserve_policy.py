from __future__ import annotations

"""Preserve a bounded legal discard option in initial D1 adaptive roots.

The semantic candidate guard intentionally gives initial Play shaping a short soft
window. Live evidence showed that difficult hands could consume that entire window
before discard generation began, leaving canonical adaptive search with a Play-only
root even while four or five real discards remained. This late wrapper does not own
Play/Discard selection. It only guarantees that an initial legal root cannot lose
all discard evidence solely because Play shaping used the soft candidate window.

The Hook is excluded while its boss effect is active. Live evidence showed that a
reserved player-discard candidate on The Hook could spend the entire D1 wall-clock
budget inside one discard projection before adaptive node 1. The boss already forces
card removal after each played hand, while bounded structural timeout recovery still
retains legal player-discard authority when it is actually needed.
"""

from time import perf_counter

from games.balatro.actions import DISCARD_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.semantic_search_guard_policy import _cheap_discard_key


_ROOT_DISCARD_RESERVE = 2


def _projection_free_discard_reserve(planner, state, actions, *, limit: int):
    """Choose a tiny deterministic discard reserve without Joker-aware projection."""
    values = list(actions)
    if limit <= 0 or not values:
        return []

    records = []
    deadline = getattr(planner, "deadline", None)
    for action in values:
        if records and deadline is not None and perf_counter() >= deadline:
            break
        try:
            key = _cheap_discard_key(state, action)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            key = (0.0, len(getattr(action, "cards", ()) or ()))
        records.append((action, key))
        if deadline is not None and perf_counter() >= deadline:
            break

    if not records:
        return values[:limit]

    ranked = sorted(records, key=lambda item: item[1], reverse=True)
    widest = max(
        records,
        key=lambda item: (
            len(getattr(item[0], "cards", ()) or ()),
            item[1],
        ),
    )[0]

    selected = [action for action, _ in ranked[:limit]]
    if widest not in selected:
        selected = selected[: max(0, limit - 1)] + [widest]
    return selected[:limit]


def _active_hook(state) -> bool:
    return (
        str(getattr(state, "boss_name", "") or "") == "The Hook"
        and not boss_blind_disabled_by_owned_jokers(state)
    )


def _candidate_actions_with_root_discard_reserve(
    original_candidate_actions,
    self,
    state,
    *,
    allow_discards: bool,
    play_width: int | None = None,
    discard_width: int | None = None,
):
    candidates = list(
        original_candidate_actions(
            self,
            state,
            allow_discards=allow_discards,
            play_width=play_width,
            discard_width=discard_width,
        )
    )

    initial_root = int(getattr(self, "nodes_evaluated", 0) or 0) == 0
    configured_discard_width = (
        int(getattr(self, "discard_width", 0) or 0)
        if discard_width is None
        else int(discard_width)
    )
    if (
        not initial_root
        or not allow_discards
        or configured_discard_width <= 0
        or int(getattr(state, "discards_remaining", 0) or 0) <= 0
        or _active_hook(state)
        or any(getattr(action, "name", None) == DISCARD_CARDS for action in candidates)
    ):
        return candidates

    deadline = getattr(self, "deadline", None)
    if deadline is not None and perf_counter() >= deadline:
        return candidates

    action_generator = getattr(self, "action_generator", None)
    generate_discards = getattr(action_generator, "generate_discard_actions", None)
    if not callable(generate_discards):
        return candidates

    try:
        legal_discards = list(generate_discards(state))
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return candidates
    if not legal_discards:
        return candidates

    reserve = _projection_free_discard_reserve(
        self,
        state,
        legal_discards,
        limit=min(_ROOT_DISCARD_RESERVE, configured_discard_width),
    )
    return candidates + reserve


def install_d1_root_discard_reserve_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_root_discard_reserve_installed", False):
        return

    original_candidate_actions = LiveBlindClearPlanner._candidate_actions

    def candidate_actions_with_root_discard_reserve(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        return _candidate_actions_with_root_discard_reserve(
            original_candidate_actions,
            self,
            state,
            allow_discards=allow_discards,
            play_width=play_width,
            discard_width=discard_width,
        )

    LiveBlindClearPlanner._candidate_actions = candidate_actions_with_root_discard_reserve
    LiveBlindClearPlanner._root_discard_reserve_installed = True
