"""Exact fail-closed headless SKIP_BLIND transition slices.

Vanilla acquires the displayed Tag, increments the run skip count, marks the
current non-Boss blind Skipped, advances to the next blind choice, notifies
Jokers, and applies Tag contexts.  This owner exposes only outcomes whose entire
reachable mutation is currently exact.  Unsupported Tags and Big-to-Boss
progression stay outside the training mask.
"""

from __future__ import annotations

from copy import deepcopy

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_requirement import red_white_base_blind_amount
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


SUPPORTED_IMMEDIATE_SKIP_TAGS = frozenset({"tag_economy"})


def skip_blind_exact(run: HeadlessRunState) -> HeadlessRunState:
    """Skip a Small Blind carrying the deterministic Economy Tag.

    Economy Tag is immediately consumed and adds
    ``min(40, max(0, dollars))`` in pinned vanilla source.  The next Big
    Blind's generated Tag must already be retained in private progression.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "BLIND_SELECT":
        raise HeadlessTransitionError("SKIP_BLIND requires BLIND_SELECT phase")
    if state.blind is None or state.blind.type is not BlindType.SMALL:
        raise HeadlessTransitionError(
            "exact SKIP_BLIND currently supports Small Blind only"
        )
    if state.boss_name is not None:
        raise HeadlessTransitionError("Small SKIP_BLIND cannot carry Boss state")
    if run.tags:
        raise HeadlessTransitionError(
            "exact SKIP_BLIND does not yet own pre-existing active Tags"
        )
    if isinstance(state.money, bool) or not isinstance(state.money, int):
        raise HeadlessTransitionError("SKIP_BLIND requires exact integer money")

    tag_key = getattr(state.blind, "tag_key", None)
    if tag_key not in SUPPORTED_IMMEDIATE_SKIP_TAGS:
        raise HeadlessTransitionError(
            f"SKIP_BLIND Tag outcome is not exact: {tag_key!r}"
        )

    progression = run.require_blind_progression_state()
    if progression.blind_ante != state.ante:
        raise HeadlessTransitionError(
            "SKIP_BLIND public Ante conflicts with private progression"
        )
    if progression.blind_on_deck != "Small" or progression.small_status != "Select":
        raise HeadlessTransitionError(
            "SKIP_BLIND requires selected Small private progression"
        )
    if progression.small_tag != tag_key:
        raise HeadlessTransitionError(
            "SKIP_BLIND public Tag conflicts with private progression"
        )
    if not progression.big_tag:
        raise HeadlessTransitionError(
            "SKIP_BLIND requires the generated next Big Blind Tag"
        )

    next_run = run.copy()
    next_progression = deepcopy(progression)
    next_progression.small_status = "Skipped"
    next_progression.big_status = "Select"
    next_progression.blind_on_deck = "Big"
    next_run.blind_progression_state = next_progression
    next_run.skips += 1

    next_state = next_run.public
    next_state.money += min(40, max(0, state.money))
    next_state.blind = Blind(
        BlindType.BIG,
        red_white_base_blind_amount(state.ante) * 3 // 2,
        reward=4,
        tag_key=next_progression.big_tag,
    )
    return next_run


def can_skip_blind_exact(run: HeadlessRunState) -> bool:
    """Return exact legality without mutating public/private/RNG state."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    try:
        skip_blind_exact(run)
    except HeadlessTransitionError:
        return False
    return True
