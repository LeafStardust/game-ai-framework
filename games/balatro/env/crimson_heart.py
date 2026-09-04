"""Exact Crimson Heart Joker-debuff lifecycle primitives.

Vanilla owns Crimson Heart across the blind/start/play/draw lifecycle:

* ``Blind:set_blind`` leaves the generic ``self.prepped = true`` state in place;
* the Joker ``setting_blind`` pass runs after that Boss state is installed;
* the initial ``Blind:drawn_to_hand`` chooses one Joker;
* ``Blind:press_play`` re-arms ``self.prepped`` when at least one Joker exists;
* the next ``Blind:drawn_to_hand`` clears existing Joker debuffs, excludes the
  previously debuffed Joker when there are at least two Jokers, then chooses one
  candidate with ``pseudorandom_element(..., pseudoseed('crimson_heart'))``.

The Blind's ``prepped`` bit is simulator-private mechanics state. Joker debuff
state itself is public and lives on each Joker as ``debuffed``.
"""

from __future__ import annotations

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_CRIMSON_HEART_KEY = "crimson_heart"


def _require_crimson(run: HeadlessRunState) -> None:
    state = run.public
    if state.boss_name != "Crimson Heart":
        raise HeadlessTransitionError("Crimson Heart effect requires Crimson Heart")
    if getattr(state.blind, "disabled", False):
        raise HeadlessTransitionError("Crimson Heart effect requires active blind state")


def set_crimson_heart_prepped(
    run: HeadlessRunState,
    value: bool,
) -> HeadlessRunState:
    """Set the source-native private ``Blind.prepped`` state on an isolated run."""
    _require_crimson(run)
    if not isinstance(value, bool):
        raise HeadlessTransitionError("Crimson Heart prepped state must be boolean")
    next_run = run.copy()
    setattr(next_run.public.blind, "prepped", value)
    return next_run


def prepare_supported_crimson_heart_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own Crimson Heart's exact pre-deal Boss lifecycle.

    The common blind-start owner installs round resources first. Crimson Heart
    has no additional ``Blind:set_blind`` mutation beyond the generic
    ``prepped = true`` state, which must exist before the Joker ``setting_blind``
    pass. Importing the common helpers lazily avoids a module cycle while keeping
    the source ordering owned by the established blind-start implementation.
    """
    from games.balatro.env.blind_start import (
        _begin_predeal_lifecycle,
        _finish_predeal_lifecycle,
        _require_boss_blind,
    )

    _require_boss_blind(run, label="Crimson Heart boss start")
    _require_crimson(run)

    next_run = _begin_predeal_lifecycle(run)
    setattr(next_run.public.blind, "prepped", True)
    return _finish_predeal_lifecycle(next_run)


def start_supported_crimson_heart(run: HeadlessRunState) -> HeadlessRunState:
    """Compose Crimson pre-deal, exact deal, and initial drawn-to-hand target."""
    prepared = prepare_supported_crimson_heart_start(run)
    dealt = deal_supported_round_start(prepared)
    return apply_crimson_heart_drawn_to_hand(dealt)


def arm_crimson_heart_after_play(
    run: HeadlessRunState,
    action: BalatroAction,
) -> HeadlessRunState:
    """Mirror Crimson Heart's ``Blind:press_play`` arming behavior.

    This owner deliberately does not execute the ordinary hand->play transition.
    It only validates a canonical PLAY_CARDS action at SELECTING_HAND and arms
    the next drawn-to-hand selection when a Joker exists.
    """
    _require_crimson(run)
    if run.public.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "Crimson Heart press-play effect requires SELECTING_HAND phase"
        )
    if not isinstance(action, BalatroAction) or action.name != PLAY_CARDS:
        raise HeadlessTransitionError("Crimson Heart press-play effect requires PLAY_CARDS")
    cards = list(action.cards or [])
    if not cards or len(cards) > 5:
        raise HeadlessTransitionError("Crimson Heart PLAY_CARDS requires 1 to 5 cards")
    if len({id(card) for card in cards}) != len(cards):
        raise HeadlessTransitionError("Crimson Heart PLAY_CARDS contains duplicate cards")
    hand_ids = {id(card) for card in run.public.hand}
    if any(id(card) not in hand_ids for card in cards):
        raise HeadlessTransitionError(
            "Crimson Heart PLAY_CARDS must reference current-hand card objects"
        )

    next_run = run.copy()
    if next_run.public.jokers:
        setattr(next_run.public.blind, "prepped", True)
    return next_run


def apply_crimson_heart_drawn_to_hand(run: HeadlessRunState) -> HeadlessRunState:
    """Choose the exact Crimson Heart Joker target at drawn-to-hand.

    ``pseudorandom_element`` sorts candidates by Joker ``sort_id``. The retained
    :class:`JokerOrderState` creation order is that exact relative order, so the
    public/physical area order never substitutes for RNG candidate ordering.
    """
    _require_crimson(run)
    if run.public.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "Crimson Heart drawn-to-hand effect requires SELECTING_HAND phase"
        )

    prepped = bool(getattr(run.public.blind, "prepped", False))
    if not prepped:
        return run.copy()

    next_run = run.copy()
    next_state = next_run.public
    jokers = list(next_state.jokers)

    # ``Blind:drawn_to_hand`` clears prepped after every invocation, even when
    # there is no Joker to target.
    setattr(next_state.blind, "prepped", False)
    if not jokers:
        return next_run

    order_state = next_run.require_joker_order_state()
    creation_order = list(order_state.creation_order)
    if len(creation_order) != len(jokers):
        raise HeadlessTransitionError(
            "Crimson Heart Joker creation order is incomplete"
        )

    if len(jokers) < 2:
        candidates = creation_order
    else:
        candidates = [
            joker for joker in creation_order
            if not bool(getattr(joker, "debuffed", False))
        ]

    # Vanilla clears every Joker before selecting the replacement target.
    for joker in jokers:
        joker.debuffed = False

    if not candidates:
        raise HeadlessTransitionError(
            "Crimson Heart has no exact eligible Joker target"
        )

    chosen_index = next_run.rng.pseudorandom_element_index(
        len(candidates),
        _CRIMSON_HEART_KEY,
    )
    candidates[chosen_index].debuffed = True
    return next_run


def clear_crimson_heart_joker_debuffs(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror active-Boss disable/defeat cleanup for Joker debuffs."""
    if run.public.boss_name != "Crimson Heart":
        raise HeadlessTransitionError("Crimson Heart cleanup requires Crimson Heart")
    next_run = run.copy()
    for joker in next_run.public.jokers:
        joker.debuffed = False
    if next_run.public.blind is not None:
        setattr(next_run.public.blind, "prepped", False)
    return next_run
