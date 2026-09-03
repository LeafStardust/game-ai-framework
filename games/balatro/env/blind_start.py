"""Exact blind-start lifecycle slices for R2 ownership.

The training action remains fail-closed. These helpers own increasingly broad
pieces of the vanilla select-blind/new-round boundary while preserving source
ordering and rejecting unclassified modifier surfaces.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.deal import (
    deal_pristine_round_start,
    deal_supported_round_start,
)
from games.balatro.env.round_lifecycle import (
    apply_round_resource_baseline,
    apply_supported_setting_blind_effects,
    consume_round_bonuses,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _require_common_blind_start_boundary(run: HeadlessRunState, *, label: str) -> None:
    state = run.public
    if state.phase != "BLIND_SELECT":
        raise HeadlessTransitionError(f"{label} requires BLIND_SELECT phase")
    if isinstance(state.round, bool) or not isinstance(state.round, int) or state.round < 0:
        raise HeadlessTransitionError("round must be an exact nonnegative integer")
    requirement = getattr(state.blind, "requirement", None)
    if isinstance(requirement, bool) or not isinstance(requirement, int) or requirement < 0:
        raise HeadlessTransitionError("blind requirement must be an exact nonnegative integer")
    if run.tags:
        raise HeadlessTransitionError(f"{label} with active tags is not yet owned")
    if state.vouchers:
        raise HeadlessTransitionError(f"{label} with vouchers is not yet owned")
    if state.hand or state.discard_pile or run.draw_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError(f"{label} requires empty transition card zones")


def _require_nonboss_blind_start_boundary(run: HeadlessRunState) -> None:
    state = run.public
    if state.blind is None or getattr(state.blind, "type", None) not in {
        BlindType.SMALL,
        BlindType.BIG,
    }:
        raise HeadlessTransitionError("nonboss blind start requires Small or Big Blind")
    _require_common_blind_start_boundary(run, label="nonboss blind start")
    if state.boss_name is not None:
        raise HeadlessTransitionError("nonboss blind start cannot have boss state")


def _apply_common_predeal_lifecycle(run: HeadlessRunState) -> HeadlessRunState:
    next_run = run.copy()
    next_state = next_run.public

    # G.FUNCS.select_blind queues ease_round(1) before new_round().
    next_state.round += 1
    next_state.blind_score = next_state.blind.requirement
    next_state.boss_blind_state_observed = False
    next_state.boss_blind_hands = set()
    next_state.boss_blind_only_hand = None

    next_run = apply_round_resource_baseline(next_run)
    next_run = apply_supported_setting_blind_effects(next_run)
    next_run = consume_round_bonuses(next_run)
    next_run.public.phase = "DRAW_TO_HAND"
    return next_run


def prepare_supported_nonboss_blind_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own select→pre-deal lifecycle for audited Small/Big Blind state."""
    _require_nonboss_blind_start_boundary(run)
    return _apply_common_predeal_lifecycle(run)


def start_supported_nonboss_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Compose audited non-boss lifecycle with the generalized exact deal."""
    prepared = prepare_supported_nonboss_blind_start(run)
    return deal_supported_round_start(prepared)


def start_supported_nonboss_blind_pristine_deck(run: HeadlessRunState) -> HeadlessRunState:
    """Backward-compatible pristine-deck composition helper."""
    prepared = prepare_supported_nonboss_blind_start(run)
    return deal_pristine_round_start(prepared)


def prepare_supported_wall_blind_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own the exact pre-deal lifecycle for The Wall.

    The Wall has no start-time card debuff, hand/discard override, or mutable boss
    state. Its enlarged target is already represented by the authoritative blind
    requirement. This slice therefore adds the Boss identity gate around the same
    source-ordered round reset → setting_blind → bonus-consumption lifecycle.
    """
    state = run.public
    if state.blind is None or getattr(state.blind, "type", None) is not BlindType.BOSS:
        raise HeadlessTransitionError("The Wall blind start requires Boss Blind")
    _require_common_blind_start_boundary(run, label="The Wall blind start")
    if state.boss_name != "The Wall":
        raise HeadlessTransitionError("The Wall blind start requires authoritative boss name")

    return _apply_common_predeal_lifecycle(run)


def start_supported_wall_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Compose exact The Wall lifecycle with generalized shuffle/deal."""
    prepared = prepare_supported_wall_blind_start(run)
    return deal_supported_round_start(prepared)


def prepare_pristine_first_small_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Apply the exact fresh Red/White first-blind pre-draw lifecycle."""
    state = run.public

    # G.GAME.round initializes at 0. G.FUNCS.select_blind queues ease_round(1)
    # before new_round(), so the first BLIND_SELECT boundary is exactly 0 -> 1.
    if state.ante != 1 or state.round != 0:
        raise HeadlessTransitionError("pristine first blind start requires ante 1 round 0")
    if state.blind is None or getattr(state.blind, "type", None) is not BlindType.SMALL:
        raise HeadlessTransitionError("pristine first blind start requires Small Blind")
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

    return prepare_supported_nonboss_blind_start(run)


def start_pristine_first_small_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Compose exact first-blind lifecycle setup with exact shuffle/deal."""
    prepared = prepare_pristine_first_small_blind(run)
    return deal_pristine_round_start(prepared)
