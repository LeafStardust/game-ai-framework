"""Compose exact post-Boss cash-out blind generation in vanilla source order.

At the Boss cash-out boundary vanilla has already advanced Ante during
``end_round`` and paid/entered the shop path.  When Boss status is Defeated it
then generates the next Ante's Small and Big skip tags, and only afterwards
``reset_blinds()`` obtains the next Boss.

This owner intentionally returns the generated skip tags explicitly rather than
burying them in ``HeadlessRunState.tags``: that field represents acquired active
Tags, whereas these are visible future blind offers and need their own eventual
BLIND_SELECT observation/state owner.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.env.blind_progression import (
    BlindProgressionError,
    BlindProgressionState,
    reset_blinds_after_boss_cashout,
)
from games.balatro.env.boss_selection import (
    BOSS_KEY_BY_NAME,
    BossSelectionError,
    BossSelectionResult,
    BossSelectionState,
    select_normal_boss,
)
from games.balatro.env.tag_selection import TagProfileState, select_normal_tag
from games.balatro.env.transition import HeadlessRunState


@dataclass(frozen=True)
class PostBossCashoutGeneration:
    """Exact generated choices plus isolated simulator-private successor state."""

    run: HeadlessRunState
    progression: BlindProgressionState
    boss_selection: BossSelectionState
    small_tag: str
    big_tag: str
    boss: BossSelectionResult


def generate_post_boss_cashout_choices(
    run: HeadlessRunState,
    progression: BlindProgressionState,
    boss_selection: BossSelectionState,
    tag_profile: TagProfileState,
) -> PostBossCashoutGeneration:
    """Generate Small Tag -> Big Tag -> next Boss, then apply ``reset_blinds``.

    Legacy callers may pass progression explicitly when the run has no retained
    private owner. If the run already retains progression, the explicit argument
    must match exactly. The successor run always retains the reset progression.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")
    if not isinstance(boss_selection, BossSelectionState):
        raise TypeError("boss_selection must be BossSelectionState")
    if not isinstance(tag_profile, TagProfileState):
        raise TypeError("tag_profile must be TagProfileState")
    if run.blind_progression_state is not None and run.blind_progression_state != progression:
        raise BlindProgressionError(
            "explicit blind progression conflicts with retained run progression"
        )

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise BlindProgressionError(
            "post-Boss generation requires active SHOP cash-out boundary"
        )
    if any(
        (
            state.shop_jokers,
            state.shop_consumables,
            state.shop_boosters,
            state.shop_vouchers,
        )
    ):
        raise BlindProgressionError(
            "post-Boss generation requires shop contents to remain ungenerated"
        )
    if progression.blind_on_deck != "Boss" or progression.boss_status != "Defeated":
        raise BlindProgressionError(
            "post-Boss generation requires defeated Boss progression"
        )
    if state.ante != progression.blind_ante + 1:
        raise BlindProgressionError(
            "post-Boss generation requires end_round Ante advancement first"
        )
    if not progression.boss_name:
        raise BlindProgressionError(
            "post-Boss generation requires the defeated Boss identity"
        )

    current_boss_key = BOSS_KEY_BY_NAME.get(progression.boss_name)
    if current_boss_key is None:
        raise BossSelectionError("defeated Boss is not a vanilla Boss identity")
    if boss_selection.usage_counts[current_boss_key] < 1:
        raise BossSelectionError(
            "Boss usage state does not record the defeated Boss selection"
        )

    # Source G.FUNCS.cash_out order: both blind tags are regenerated before
    # reset_blinds() calls get_new_boss().
    next_run, small_tag = select_normal_tag(
        run,
        tag_profile,
        ante=state.ante,
    )
    next_run, big_tag = select_normal_tag(
        next_run,
        tag_profile,
        ante=state.ante,
    )
    next_run, next_boss_selection, next_boss = select_normal_boss(
        next_run,
        boss_selection,
        ante=state.ante,
    )
    next_progression = reset_blinds_after_boss_cashout(
        progression,
        current_ante=state.ante,
        next_boss_name=next_boss.boss_name,
    )
    next_progression.small_tag = small_tag
    next_progression.big_tag = big_tag
    next_run.blind_progression_state = deepcopy(next_progression)

    return PostBossCashoutGeneration(
        run=next_run,
        progression=next_progression,
        boss_selection=next_boss_selection,
        small_tag=small_tag,
        big_tag=big_tag,
        boss=next_boss,
    )
