"""Exact retained-deck blind start for Chicot disabling The Manacle.

This is intentionally narrower than the generic resource-Boss start owner.  It
exists to prove the one source-order boundary that requires physical deck state
from the previous round:

1. enter The Manacle blind from BLIND_SELECT;
2. apply round resource baseline;
3. Manacle reduces hand size by one;
4. setting-blind Jokers run;
5. Chicot queues and executes ``Blind:disable``;
6. Manacle restores hand size and draws the retained physical deck tail;
7. later ``nr{ante}`` shuffle re-sorts/shuffles only the remaining cards;
8. ordinary draw fills the restored hand.

The canonical training ``SELECT_BLIND`` action remains hidden; this helper is an
R2 mechanics owner only.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.blind_start import (
    _begin_predeal_lifecycle,
    _finish_predeal_lifecycle,
)
from games.balatro.env.boss_resources import apply_resource_boss_start
from games.balatro.env.predeal_continuation import deal_after_retained_preblind_draw
from games.balatro.env.round_zones import require_full_retained_preblind_deck
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.chicot import ChicotJoker


def _require_retained_manacle_chicot_boundary(run: HeadlessRunState) -> None:
    state = run.public
    if state.phase != "BLIND_SELECT":
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start requires BLIND_SELECT phase"
        )
    if state.blind is None or getattr(state.blind, "type", None) is not BlindType.BOSS:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start requires Boss Blind"
        )
    if state.boss_name != "The Manacle":
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start requires The Manacle"
        )
    if isinstance(state.round, bool) or not isinstance(state.round, int) or state.round < 0:
        raise HeadlessTransitionError("round must be an exact nonnegative integer")
    requirement = getattr(state.blind, "requirement", None)
    if isinstance(requirement, bool) or not isinstance(requirement, int) or requirement < 0:
        raise HeadlessTransitionError(
            "blind requirement must be an exact nonnegative integer"
        )
    if run.tags:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start with active tags is not yet owned"
        )
    if state.vouchers:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start with vouchers is not yet owned"
        )
    if state.hand or state.discard_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start requires empty hand/discard/play zones"
        )

    chicot_count = sum(type(joker) is ChicotJoker for joker in state.jokers)
    if chicot_count != 1:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot start requires exactly one Chicot"
        )

    require_full_retained_preblind_deck(run)


def prepare_retained_manacle_chicot_start(run: HeadlessRunState) -> HeadlessRunState:
    """Run exact pre-deal lifecycle through Chicot's one retained tail draw."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    _require_retained_manacle_chicot_boundary(run)

    next_run = _begin_predeal_lifecycle(run)
    next_run = apply_resource_boss_start(next_run)
    next_run = _finish_predeal_lifecycle(next_run)

    if not bool(getattr(next_run.public.blind, "disabled", False)):
        raise HeadlessTransitionError(
            "retained Manacle+Chicot pre-deal lifecycle did not disable the Boss"
        )
    if next_run.boss_hand_size_sub is not None:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot pre-deal lifecycle left hand-size reversal state"
        )
    if len(next_run.public.hand) != 1:
        raise HeadlessTransitionError(
            "retained Manacle+Chicot pre-deal lifecycle must draw exactly one card"
        )
    return next_run


def start_retained_manacle_chicot(run: HeadlessRunState) -> HeadlessRunState:
    """Compose exact pre-deal disable with remaining-card shuffle/initial draw."""
    prepared = prepare_retained_manacle_chicot_start(run)
    return deal_after_retained_preblind_draw(prepared)
