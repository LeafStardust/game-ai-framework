"""Exact card-facing lifecycle for Balatro Boss Blinds.

Balatro keeps the true physical card identity while rendering some hand cards
face down.  Headless mechanics retain that identity internally, while the
policy-facing observation layer masks it.  This module owns only source-audited
facing transitions; unsupported timing/RNG cases remain separate.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.blind_start import (
    _apply_common_predeal_lifecycle,
    _require_boss_blind,
)
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.hand_rules import card_is_face, hand_rules_for_state


_DETERMINISTIC_FACING_BOSS_NAMES = frozenset({"The House", "The Mark"})
_FACING_BOSS_NAMES = frozenset({"The House", "The Wheel", "The Mark", "The Fish"})


def _require_round_play_history(state) -> int:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        raise HeadlessTransitionError("facing Boss requires exact current-round hand history")
    total = 0
    for value in counts.values():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise HeadlessTransitionError(
                "facing Boss requires exact nonnegative current-round hand history"
            )
        total += value
    return total


def deterministic_card_stays_face_down(state, card: BalatroCard) -> bool:
    """Mirror deterministic ``Blind:stay_flipped`` cases for one hand draw.

    The House checks whether *any* play or discard has happened this round.
    The Mark delegates to ``Card:is_face(true)``; the ``from_boss`` argument
    ignores card debuff state but still honors Pareidolia, which is represented
    by the canonical passive hand-rule pipeline.
    """
    if not isinstance(card, BalatroCard):
        raise HeadlessTransitionError("facing Boss draw requires BalatroCard")

    boss_name = state.boss_name
    if boss_name == "The House":
        plays = _require_round_play_history(state)
        discards_used = state.discards_used
        if (
            isinstance(discards_used, bool)
            or not isinstance(discards_used, int)
            or discards_used < 0
        ):
            raise HeadlessTransitionError(
                "The House requires exact nonnegative discard history"
            )
        return plays == 0 and discards_used == 0

    if boss_name == "The Mark":
        return card_is_face(card, hand_rules_for_state(state))

    raise HeadlessTransitionError("Boss is not in the deterministic facing set")


def apply_deterministic_facing_to_current_hand(run: HeadlessRunState) -> HeadlessRunState:
    """Apply exact House/Mark facing to every card just drawn into the hand.

    This helper is intentionally for a draw boundary where every current hand
    card belongs to the just-completed draw batch, such as the initial round-start
    deal.  Later partial draws should apply the same predicate only to the newly
    moved physical cards rather than re-flipping older hand cards.
    """
    state = run.public
    if state.boss_name not in _DETERMINISTIC_FACING_BOSS_NAMES:
        raise HeadlessTransitionError("Boss is not in the deterministic facing set")
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "deterministic facing draw requires SELECTING_HAND phase"
        )

    # Validate the full transition before cloning/mutating anything.
    decisions = [deterministic_card_stays_face_down(state, card) for card in state.hand]

    next_run = run.copy()
    for card, face_down in zip(next_run.public.hand, decisions, strict=True):
        card.face_down = bool(face_down)
        card.facing_observed = True
    return next_run


def prepare_supported_deterministic_facing_boss_start(
    run: HeadlessRunState,
) -> HeadlessRunState:
    """Own the ordinary pre-deal lifecycle for The House and The Mark."""
    _require_boss_blind(run, label="deterministic facing boss start")
    if run.public.boss_name not in _DETERMINISTIC_FACING_BOSS_NAMES:
        raise HeadlessTransitionError(
            "boss is not in the audited deterministic facing start set"
        )
    return _apply_common_predeal_lifecycle(run)


def start_supported_deterministic_facing_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Compose House/Mark pre-deal, exact shuffle/deal, and facing state."""
    prepared = prepare_supported_deterministic_facing_boss_start(run)
    dealt = deal_supported_round_start(prepared)
    return apply_deterministic_facing_to_current_hand(dealt)


def clear_facing_boss_hand(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror facing cleanup performed by ``Blind:disable``/Boss defeat.

    Vanilla flips every remaining face-down hand card face up for The Wheel,
    The House, The Mark, and The Fish.  ``wheel_flipped`` is UI/deck-preview
    bookkeeping; no additional headless mechanical state is required once the
    authoritative facing value itself is owned.
    """
    if run.public.boss_name not in _FACING_BOSS_NAMES:
        raise HeadlessTransitionError("facing cleanup requires a facing Boss")

    next_run = run.copy()
    for card in next_run.public.hand:
        card.face_down = False
        card.facing_observed = True
    return next_run
