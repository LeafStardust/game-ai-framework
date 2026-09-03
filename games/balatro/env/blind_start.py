"""Exact blind-start lifecycle slices for R2 ownership.

The training action remains fail-closed. These helpers own increasingly broad
pieces of the vanilla select-blind/new-round boundary while preserving source
ordering and rejecting unclassified modifier surfaces.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.boss_debuffs import (
    apply_plant_face_debuff,
    apply_static_suit_boss_debuff,
)
from games.balatro.env.boss_resources import apply_resource_boss_start
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


_REQUIREMENT_ONLY_BOSS_NAMES = frozenset({"The Wall", "Violet Vessel"})
_MUTABLE_HAND_RULE_BOSS_NAMES = frozenset({"The Eye", "The Mouth"})
_RESOURCE_MUTATING_BOSS_NAMES = frozenset({"The Water", "The Needle", "The Manacle"})
_STATIC_SUIT_DEBUFF_BOSS_NAMES = frozenset({"The Goad", "The Window", "The Head", "The Club"})


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


def _require_boss_blind(run: HeadlessRunState, *, label: str) -> None:
    state = run.public
    if state.blind is None or getattr(state.blind, "type", None) is not BlindType.BOSS:
        raise HeadlessTransitionError(f"{label} requires Boss Blind")
    _require_common_blind_start_boundary(run, label=label)


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


def _begin_predeal_lifecycle(run: HeadlessRunState) -> HeadlessRunState:
    """Apply source-ordered round increment, target install, and resource reset."""
    next_run = run.copy()
    next_state = next_run.public

    # G.FUNCS.select_blind queues ease_round(1) before new_round().
    next_state.round += 1
    next_state.blind_score = next_state.blind.requirement
    next_state.boss_blind_state_observed = False
    next_state.boss_blind_hands = set()
    next_state.boss_blind_only_hand = None
    return apply_round_resource_baseline(next_run)


def _finish_predeal_lifecycle(run: HeadlessRunState) -> HeadlessRunState:
    """Apply setting_blind Jokers after Blind:set_blind state, then consume bonus."""
    next_run = apply_supported_setting_blind_effects(run)
    next_run = consume_round_bonuses(next_run)
    next_run.public.phase = "DRAW_TO_HAND"
    return next_run


def _apply_common_predeal_lifecycle(run: HeadlessRunState) -> HeadlessRunState:
    return _finish_predeal_lifecycle(_begin_predeal_lifecycle(run))


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


def prepare_supported_requirement_only_boss_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own Boss starts whose only start-time mechanic is their requirement."""
    _require_boss_blind(run, label="requirement-only boss start")
    if run.public.boss_name not in _REQUIREMENT_ONLY_BOSS_NAMES:
        raise HeadlessTransitionError(
            "boss is not in the audited requirement-only start set"
        )
    return _apply_common_predeal_lifecycle(run)


def start_supported_requirement_only_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Compose an audited requirement-only Boss start with exact shuffle/deal."""
    prepared = prepare_supported_requirement_only_boss_start(run)
    return deal_supported_round_start(prepared)


def prepare_supported_mutable_hand_rule_boss_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own exact start state for The Eye and The Mouth.

    Vanilla ``Blind:set_blind`` initializes The Eye's per-hand usage table and
    The Mouth's selected-hand restriction *after* round resources are reset but
    *before* the Joker ``setting_blind`` pass. Canonical public state represents
    those mutable structures directly:

    * Eye: observed mutable state with no hands used yet;
    * Mouth: observed mutable state with no hand locked yet.
    """
    _require_boss_blind(run, label="mutable hand-rule boss start")
    state = run.public
    if state.boss_name not in _MUTABLE_HAND_RULE_BOSS_NAMES:
        raise HeadlessTransitionError(
            "boss is not in the audited mutable hand-rule start set"
        )

    next_run = _begin_predeal_lifecycle(run)
    next_state = next_run.public
    next_state.boss_blind_state_observed = True
    next_state.boss_blind_hands = set()
    next_state.boss_blind_only_hand = None
    return _finish_predeal_lifecycle(next_run)


def start_supported_mutable_hand_rule_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Compose Eye/Mouth start state with exact shuffle/deal."""
    prepared = prepare_supported_mutable_hand_rule_boss_start(run)
    return deal_supported_round_start(prepared)


def prepare_supported_resource_boss_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own exact Water/Needle/Manacle start ordering and reversible private state.

    Vanilla applies the Boss resource mutation after the generic round-resource
    baseline and before the Joker ``setting_blind`` pass. Water stores and
    removes current post-bonus discards; Needle stores ``round_resets.hands - 1``
    and removes exactly that amount, leaving one-shot hand bonuses intact;
    Manacle stores and removes exactly one hand-size slot before the initial deal.
    """
    _require_boss_blind(run, label="resource-mutating boss start")
    if run.public.boss_name not in _RESOURCE_MUTATING_BOSS_NAMES:
        raise HeadlessTransitionError(
            "boss is not in the audited resource-mutating start set"
        )

    next_run = _begin_predeal_lifecycle(run)
    next_run = apply_resource_boss_start(next_run)
    return _finish_predeal_lifecycle(next_run)


def start_supported_resource_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Compose audited resource-Boss lifecycle with exact generalized shuffle/deal."""
    prepared = prepare_supported_resource_boss_start(run)
    return deal_supported_round_start(prepared)


def prepare_supported_static_suit_debuff_boss_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own exact Goad/Window/Head/Club pre-deal card debuff ordering."""
    _require_boss_blind(run, label="static suit-debuff boss start")
    if run.public.boss_name not in _STATIC_SUIT_DEBUFF_BOSS_NAMES:
        raise HeadlessTransitionError(
            "boss is not in the audited static suit-debuff start set"
        )

    next_run = _begin_predeal_lifecycle(run)
    next_run = apply_static_suit_boss_debuff(next_run)
    return _finish_predeal_lifecycle(next_run)


def start_supported_static_suit_debuff_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Compose static suit-debuff Boss state with exact shuffle/deal."""
    prepared = prepare_supported_static_suit_debuff_boss_start(run)
    return deal_supported_round_start(prepared)


def prepare_supported_plant_start(run: HeadlessRunState) -> HeadlessRunState:
    """Own The Plant's source-ordered face-card debuff start."""
    _require_boss_blind(run, label="Plant boss start")
    if run.public.boss_name != "The Plant":
        raise HeadlessTransitionError("Plant boss start requires The Plant")

    next_run = _begin_predeal_lifecycle(run)
    next_run = apply_plant_face_debuff(next_run)
    return _finish_predeal_lifecycle(next_run)


def start_supported_plant(run: HeadlessRunState) -> HeadlessRunState:
    """Compose The Plant face-card debuff lifecycle with exact shuffle/deal."""
    prepared = prepare_supported_plant_start(run)
    return deal_supported_round_start(prepared)


def prepare_supported_wall_blind_start(run: HeadlessRunState) -> HeadlessRunState:
    """Backward-compatible exact The Wall pre-deal wrapper."""
    if run.public.boss_name != "The Wall":
        raise HeadlessTransitionError("The Wall blind start requires authoritative boss name")
    return prepare_supported_requirement_only_boss_start(run)


def start_supported_wall_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Backward-compatible exact The Wall shuffle/deal wrapper."""
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
