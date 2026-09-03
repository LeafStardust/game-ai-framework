"""Exact reversible resource mutations for audited Boss blinds.

Vanilla ``Blind:set_blind`` applies these mutations after the round-resource
baseline and before Joker ``setting_blind`` effects. ``Blind:disable`` later
adds the stored amount back. Normal ``Blind:defeat`` is a distinct boundary:
Manacle restores hand size without drawing, while Water/Needle simply discard
their now-irrelevant stored reversal values as the Blind is torn down.
"""

from __future__ import annotations

from games.balatro.env.deal import draw_one_supported_card_to_hand
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_RESOURCE_BOSS_NAMES = frozenset({"The Water", "The Needle", "The Manacle"})


def apply_resource_boss_start(run: HeadlessRunState) -> HeadlessRunState:
    """Apply exact audited ``Blind:set_blind`` resource mutation."""
    state = run.public
    if state.boss_name not in _RESOURCE_BOSS_NAMES:
        raise HeadlessTransitionError("boss has no audited reversible resource start")
    if (
        run.boss_hands_sub is not None
        or run.boss_discards_sub is not None
        or run.boss_hand_size_sub is not None
    ):
        raise HeadlessTransitionError("reversible boss resource adjustment is already active")

    next_run = run.copy()
    next_state = next_run.public

    if next_state.boss_name == "The Water":
        amount = next_state.discards_remaining
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise HeadlessTransitionError(
                "Water requires exact nonnegative current discards"
            )
        next_run.boss_discards_sub = amount
        next_state.discards_remaining -= amount
        return next_run

    if next_state.boss_name == "The Needle":
        if not next_state.round_reset_hands_observed:
            raise HeadlessTransitionError(
                "Needle requires authoritative round-reset hands"
            )
        reset_hands = next_state.round_reset_hands
        if (
            isinstance(reset_hands, bool)
            or not isinstance(reset_hands, int)
            or reset_hands < 0
        ):
            raise HeadlessTransitionError(
                "Needle requires exact nonnegative round-reset hands"
            )
        amount = reset_hands - 1
        next_run.boss_hands_sub = amount
        next_state.hands_remaining -= amount
        if next_state.hands_remaining < 0:
            raise HeadlessTransitionError(
                "Needle start produced negative current hands"
            )
        return next_run

    # Vanilla The Manacle: G.hand:change_size(-1)
    if next_state.hand_size < 1:
        raise HeadlessTransitionError(
            "Manacle requires positive current hand size"
        )
    next_run.boss_hand_size_sub = 1
    next_state.hand_size -= 1
    return next_run


def disable_resource_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror audited ``Blind:disable`` restoration and clear private state."""
    state = run.public
    next_run = run.copy()
    next_state = next_run.public

    if state.boss_name == "The Water":
        amount = next_run.boss_discards_sub
        if amount is None:
            raise HeadlessTransitionError("Water disable requires stored discards_sub")
        next_state.discards_remaining += amount
        next_run.boss_discards_sub = None
        return next_run

    if state.boss_name == "The Needle":
        amount = next_run.boss_hands_sub
        if amount is None:
            raise HeadlessTransitionError("Needle disable requires stored hands_sub")
        next_state.hands_remaining += amount
        next_run.boss_hands_sub = None
        return next_run

    if state.boss_name == "The Manacle":
        amount = next_run.boss_hand_size_sub
        if amount is None:
            raise HeadlessTransitionError("Manacle disable requires stored hand_size_sub")
        if amount != 1:
            raise HeadlessTransitionError("Manacle stored hand_size_sub must equal one")

        # Vanilla Blind:disable performs change_size(+1) and immediately
        # draw_from_deck_to_hand(1). The latter is exact only once headless owns
        # the shuffled physical draw pile (post initial deal). Pre-deal disable,
        # e.g. future Chicot support during setting_blind, remains fail-closed.
        next_state.hand_size += amount
        next_run.boss_hand_size_sub = None
        return draw_one_supported_card_to_hand(next_run)

    raise HeadlessTransitionError("boss has no audited reversible resource disable")


def defeat_resource_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror resource-Boss state cleanup at normal ``Blind:defeat``.

    Current-round hands/discards need no restoration for Water/Needle because the
    round has ended; vanilla tears down the Blind and drops those stored values.
    Manacle is different because hand size persists across rounds, so its one-slot
    reduction must be restored here. Unlike ``Blind:disable``, defeat does not
    draw a replacement card.
    """
    state = run.public
    if state.boss_name not in _RESOURCE_BOSS_NAMES:
        raise HeadlessTransitionError("boss has no audited resource defeat cleanup")

    next_run = run.copy()
    if state.boss_name == "The Water":
        if next_run.boss_discards_sub is None:
            raise HeadlessTransitionError("Water defeat requires stored discards_sub")
        next_run.boss_discards_sub = None
        return next_run

    if state.boss_name == "The Needle":
        if next_run.boss_hands_sub is None:
            raise HeadlessTransitionError("Needle defeat requires stored hands_sub")
        next_run.boss_hands_sub = None
        return next_run

    amount = next_run.boss_hand_size_sub
    if amount is None:
        raise HeadlessTransitionError("Manacle defeat requires stored hand_size_sub")
    if amount != 1:
        raise HeadlessTransitionError("Manacle stored hand_size_sub must equal one")
    next_run.public.hand_size += amount
    next_run.boss_hand_size_sub = None
    return next_run
