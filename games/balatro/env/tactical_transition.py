"""Exact headless tactical transitions for Phase R4.

The strategic environment deliberately does not expose card-level Play/Discard
choices to the learner. This module owns the exact simulator side of those
choices as they are admitted. Source-order Play lifecycle ownership lives in
``play_transition``; this module keeps the production decision-engine bridge and
the narrow exact Discard owner.
"""

from __future__ import annotations

from collections.abc import Iterable

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.env.deal import draw_one_supported_card_to_hand
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.round_zones import (
    normalize_visible_card_indices,
    require_exact_selecting_hand_zones,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _require_baseline_discard_callbacks_exact(run: HeadlessRunState) -> None:
    state = run.public
    if state.boss_name is not None:
        raise HeadlessTransitionError(
            "R4 baseline discard does not yet own boss discard callbacks"
        )
    if state.jokers:
        raise HeadlessTransitionError(
            "R4 baseline discard does not yet own Joker discard callbacks"
        )


def apply_supported_tactical_discard(
    run: HeadlessRunState,
    card_indices: Iterable[int],
) -> HeadlessRunState:
    """Apply one exact baseline Discard and redraw from retained physical order.

    ``card_indices`` are zero-based positions in the currently visible hand. The
    input state is never mutated. This first R4 slice deliberately rejects Boss
    and Joker discard callbacks and Purple-seal generation; later slices can
    widen the boundary only after those source-order effects are owned exactly.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError("tactical discard requires SELECTING_HAND phase")
    if state.discards_remaining <= 0:
        raise HeadlessTransitionError("tactical discard requires a remaining discard")
    if (
        isinstance(state.discards_used, bool)
        or not isinstance(state.discards_used, int)
        or state.discards_used < 0
    ):
        raise HeadlessTransitionError(
            "tactical discard requires authoritative discards_used"
        )

    indices = normalize_visible_card_indices(card_indices, hand_size=len(state.hand))
    _require_baseline_discard_callbacks_exact(run)
    require_exact_selecting_hand_zones(run)

    selected = [state.hand[index] for index in indices]
    if any(str(getattr(card, "seal", "") or "").upper() == "PURPLE" for card in selected):
        raise HeadlessTransitionError(
            "R4 baseline discard does not yet own Purple Seal generation"
        )

    next_run = run.copy()
    next_state = next_run.public
    next_selected = [next_state.hand[index] for index in indices]
    selected_ids = {id(card) for card in next_selected}

    # Vanilla discard callbacks fire before movement. All callback-producing
    # identities admitted above are absent, so the exact remaining movement is
    # hand-area order -> discard tail.
    next_state.hand = [card for card in next_state.hand if id(card) not in selected_ids]
    next_run.discard_pile.extend(next_selected)
    next_state.discard_pile.extend(next_selected)
    next_state.discards_remaining -= 1
    next_state.discards_used += 1

    # Normal non-Serpent redraw fills the hand to capacity from the retained
    # physical deck tail. Each primitive draw also restores vanilla hand sort and
    # canonicalizes the public deck without exposing hidden draw order.
    while len(next_run.public.hand) < next_run.public.hand_size and next_run.draw_pile:
        next_run = draw_one_supported_card_to_hand(next_run)

    return next_run


def _selected_observation_indices(observation, action: BalatroAction) -> tuple[int, ...]:
    selected = list(getattr(action, "cards", ()) or ())
    if not selected:
        raise HeadlessTransitionError("tactical decision returned no selected cards")

    hand = list(observation.hand)
    positions = {id(card): index for index, card in enumerate(hand)}
    try:
        indices = tuple(positions[id(card)] for card in selected)
    except KeyError as exc:
        raise HeadlessTransitionError(
            "tactical decision selected a card outside its public observation"
        ) from exc
    return normalize_visible_card_indices(indices, hand_size=len(hand))


def apply_planned_tactical_step(run: HeadlessRunState, decision_engine) -> HeadlessRunState:
    """Decide from one policy-safe observation and execute one admitted tactical step.

    R4 intentionally calls the same production-shaped ``decide(state)`` boundary
    used by the live hand-action engine. The returned decision must carry the
    canonical ``BalatroAction`` in ``decision.action``. The same sanitized
    observation object is used both for decision input and for mapping selected
    card objects back to visible positions. No hidden card identity or physical
    draw order is supplied to the decision engine.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if run.public.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "planned tactical step requires SELECTING_HAND phase"
        )

    decide_method = getattr(decision_engine, "decide", None)
    if not callable(decide_method):
        raise TypeError("decision_engine must provide decide(state)")

    observation = public_observation_state(run.public)
    decision = decide_method(observation)
    action = getattr(decision, "action", None)
    if not isinstance(action, BalatroAction):
        raise HeadlessTransitionError(
            "tactical decision engine did not return BalatroAction"
        )

    if action.name == DISCARD_CARDS:
        return apply_supported_tactical_discard(
            run,
            _selected_observation_indices(observation, action),
        )
    if action.name == PLAY_CARDS:
        return apply_supported_ordinary_play(
            run,
            _selected_observation_indices(observation, action),
        )
    raise HeadlessTransitionError(
        f"tactical decision engine returned unsupported action {action.name!r}"
    )
