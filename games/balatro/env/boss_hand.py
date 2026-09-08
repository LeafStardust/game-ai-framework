"""Exact Boss effects that fire at Balatro's ``Blind:debuff_hand`` boundary.

These helpers own only source-audited mutations after a poker hand has already
been classified. They do not execute the complete PLAY_CARDS transition.
"""

from __future__ import annotations

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _require_classified_hand(run: HeadlessRunState, hand_name: str, *, boss_name: str) -> None:
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            f"{boss_name} debuff-hand effect requires SELECTING_HAND phase"
        )
    if str(getattr(state, "boss_name", "") or "") != boss_name:
        raise HeadlessTransitionError(
            f"{boss_name} debuff-hand effect requires {boss_name}"
        )
    if not isinstance(hand_name, str) or hand_name not in state.hand_levels:
        raise HeadlessTransitionError(
            f"{boss_name} requires a canonical classified hand name"
        )


def apply_ox_debuff_hand_economy(
    run: HeadlessRunState,
    hand_name: str,
) -> HeadlessRunState:
    """Apply The Ox's exact ``matching hand -> dollars = 0`` mutation.

    Vanilla compares the classified hand name against the fixed public
    ``G.GAME.current_round.most_played_poker_hand`` value and, on an actual
    (``check == false``) hand evaluation, executes
    ``ease_dollars(-G.GAME.dollars, true)``. That always produces exactly zero,
    including when current dollars are already negative.

    The input run is never mutated. Missing/unknown target state fails closed;
    recomputing a target from aggregate hand counters is not equivalent because
    those counters can change during the current ante.
    """
    _require_classified_hand(run, hand_name, boss_name="The Ox")
    state = run.public

    target = state.round_most_played_hand
    if not isinstance(target, str) or target not in state.hand_levels:
        raise HeadlessTransitionError(
            "Ox requires authoritative current-round most-played hand state"
        )

    next_run = run.copy()
    if boss_blind_disabled_by_owned_jokers(next_run.public):
        return next_run

    if hand_name == target:
        next_run.public.money = 0
    return next_run


def apply_arm_debuff_hand_level(
    run: HeadlessRunState,
    hand_name: str,
) -> HeadlessRunState:
    """Apply The Arm's exact hand-level decrement at ``Blind:debuff_hand``.

    Vanilla mutates only when ``G.GAME.hands[handname].level > 1`` and then calls
    ``level_up_hand(..., -1)`` before ordinary scoring. Canonical scoring already
    derives base Chips/Mult from ``BalatroState.hand_levels``, so the exact
    persistent mechanic is the level decrement itself; no duplicate Chips/Mult
    fields are introduced.
    """
    _require_classified_hand(run, hand_name, boss_name="The Arm")
    level = run.public.hand_levels[hand_name]
    if isinstance(level, bool) or not isinstance(level, int) or level < 1:
        raise HeadlessTransitionError("Arm requires an exact positive hand level")

    next_run = run.copy()
    if boss_blind_disabled_by_owned_jokers(next_run.public):
        return next_run

    if level > 1:
        next_run.public.hand_levels[hand_name] = level - 1
    return next_run
