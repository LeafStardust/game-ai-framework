"""Exact first-blind lifecycle slice for R2 blind-start ownership.

This module intentionally starts with the one blind-start state whose complete
pre-deal lifecycle is already provable without shop/tag/Joker bonus semantics:
the fresh Red Deck / White Stake Ante-1 Small Blind before any shop has occurred.

It does not expose SELECT_BLIND to training yet.  Later blind starts must widen
this boundary only after their round bonuses, Joker ``setting_blind`` effects,
and boss setup are exact.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.deal import deal_pristine_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def prepare_pristine_first_small_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Apply the deterministic pre-draw lifecycle for the fresh first blind."""
    state = run.public

    if state.phase != "BLIND_SELECT":
        raise HeadlessTransitionError("first blind start requires BLIND_SELECT phase")
    if state.ante != 1 or state.round != 1:
        raise HeadlessTransitionError("pristine first blind start requires ante 1 round 1")
    if state.blind is None or getattr(state.blind, "type", None) is not BlindType.SMALL:
        raise HeadlessTransitionError("pristine first blind start requires Small Blind")
    if state.boss_name is not None:
        raise HeadlessTransitionError("pristine first blind start cannot have boss state")
    if state.jokers or state.vouchers or state.consumables or run.tags or run.skips:
        raise HeadlessTransitionError(
            "pristine first blind start requires no acquired run modifiers"
        )
    if not state.round_reset_hands_observed or not state.round_reset_discards_observed:
        raise HeadlessTransitionError(
            "first blind start requires authoritative round-reset allowances"
        )
    if state.round_reset_hands != 4 or state.round_reset_discards != 3:
        raise HeadlessTransitionError(
            "pristine Red/White first blind requires vanilla 4-hand/3-discard reset"
        )
    if run.round_bonus_hands != 0 or run.round_bonus_discards != 0:
        raise HeadlessTransitionError(
            "pristine first blind requires zero pending round bonuses"
        )
    if state.hand or state.discard_pile or run.draw_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError("first blind start requires empty card zones")

    next_run = run.copy()
    next_state = next_run.public

    # Vanilla new_round resets current-round counters before entering DRAW_TO_HAND.
    next_state.score = 0
    next_state.blind_score = next_state.blind.requirement
    next_state.hands_remaining = next_state.round_reset_hands
    next_state.discards_remaining = next_state.round_reset_discards
    next_state.discards_used = 0
    next_state.last_played_hand = None
    next_state.round_hand_play_counts = {
        hand: 0 for hand in next_state.round_hand_play_counts
    }
    next_state.boss_blind_state_observed = False
    next_state.boss_blind_hands = set()
    next_state.boss_blind_only_hand = None
    next_state.phase = "DRAW_TO_HAND"

    return next_run


def start_pristine_first_small_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Compose exact first-blind lifecycle setup with exact shuffle/deal."""
    prepared = prepare_pristine_first_small_blind(run)
    return deal_pristine_round_start(prepared)
