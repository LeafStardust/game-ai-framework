"""Compose the currently-owned normal Boss win/cash-out lifecycle in source order.

This is an internal deterministic R2 transition, not a new training-visible
action.  It joins owners that were deliberately developed and tested separately:

1. won ``end_round`` progression (including Boss Ante advancement);
2. exact supported Boss teardown + baseline payout into an ungenerated SHOP;
3. next-Ante Small Tag -> Big Tag -> Boss generation;
4. ``reset_blinds()`` progression state.

Shop inventory generation, voucher economy modifiers, active Tag cash-out effects,
and any unsupported end-of-round Joker effects still fail closed in their
existing canonical owners.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.blind_progression import (
    BlindProgressionState,
    finalize_won_round_progression,
)
from games.balatro.env.boss_cash_out import cash_out_supported_boss
from games.balatro.env.boss_cashout_generation import (
    PostBossCashoutGeneration,
    generate_post_boss_cashout_choices,
)
from games.balatro.env.boss_selection import BossSelectionState
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.transition import HeadlessRunState


@dataclass(frozen=True)
class BossRoundResolution:
    """Exact successor state after the owned Boss round/cash-out chain."""

    run: HeadlessRunState
    progression: BlindProgressionState
    boss_selection: BossSelectionState
    small_tag: str
    big_tag: str
    next_boss_key: str
    next_boss_name: str


def resolve_supported_boss_round(
    run: HeadlessRunState,
    progression: BlindProgressionState,
    boss_selection: BossSelectionState,
    tag_profile: TagProfileState,
) -> BossRoundResolution:
    """Resolve one supported cleared Boss through the exact owned cash-out chain.

    Inputs are never mutated.  The result stops at the active, ungenerated SHOP
    boundary after the next Ante's blind choices have been generated privately.
    It intentionally does not generate shop contents or enter BLIND_SELECT.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")
    if not isinstance(boss_selection, BossSelectionState):
        raise TypeError("boss_selection must be BossSelectionState")
    if not isinstance(tag_profile, TagProfileState):
        raise TypeError("tag_profile must be TagProfileState")

    progressed_run, progressed_state = finalize_won_round_progression(
        run,
        progression,
        blind_type="Boss",
    )
    paid_run = cash_out_supported_boss(progressed_run)
    generated: PostBossCashoutGeneration = generate_post_boss_cashout_choices(
        paid_run,
        progressed_state,
        boss_selection,
        tag_profile,
    )

    return BossRoundResolution(
        run=generated.run,
        progression=generated.progression,
        boss_selection=generated.boss_selection,
        small_tag=generated.small_tag,
        big_tag=generated.big_tag,
        next_boss_key=generated.boss.boss_key,
        next_boss_name=generated.boss.boss_name,
    )
