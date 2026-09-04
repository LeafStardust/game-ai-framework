"""Exact Boss-defeat -> cash-out -> ungenerated-shop composition for R2.9.

This module deliberately stops at the same SHOP boundary as ordinary cash-out.
Vanilla advances to the next Ante/Blind-select lifecycle later, when the shop is
left; folding that progression into Boss cash-out would create a non-existent
headless action boundary.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.boss_defeat import defeat_supported_boss
from games.balatro.env.round_end import (
    _ROUND_END_DOLLAR_JOKER_TYPES,
    _ROUND_END_INERT_JOKER_TYPES,
    _round_end_joker_dollars,
    baseline_interest_dollars,
)
from games.balatro.env.round_zones import repopulate_round_end_deck
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _require_exact_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HeadlessTransitionError(f"{name} must be an exact integer")
    return value


def cash_out_supported_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Cash out one defeated Boss whose normal teardown is exactly owned.

    Source-order ownership at this boundary is:

    1. capture the active Boss reward/target before Blind reset;
    2. run exact normal ``Blind:defeat`` cleanup;
    3. compute reward, unused-hand dollars, supported Joker dollar rows, and
       interest from *pre-payout* money;
    4. repopulate permanent playing cards into the round-end deck;
    5. enter an active but ungenerated SHOP.

    Boss-specific Ante progression, tags, Voucher economy modifiers, and shop RNG
    remain separate owners and therefore fail closed here.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "ROUND_EVAL":
        raise HeadlessTransitionError("Boss cash-out requires ROUND_EVAL phase")
    if state.blind is None or getattr(state.blind, "type", None) is not BlindType.BOSS:
        raise HeadlessTransitionError("Boss cash-out requires active Boss Blind")
    if not state.boss_name:
        raise HeadlessTransitionError("Boss cash-out requires authoritative boss name")

    score = _require_exact_int("score", state.score)
    requirement = _require_exact_int(
        "blind requirement", getattr(state.blind, "requirement", None)
    )
    reward = _require_exact_int("blind reward", getattr(state.blind, "reward", None))
    money = _require_exact_int("money", state.money)
    hands_remaining = _require_exact_int("hands_remaining", state.hands_remaining)

    if requirement < 0 or reward < 0 or hands_remaining < 0:
        raise HeadlessTransitionError("Boss cash-out requires nonnegative reward/resource state")
    if money < 0:
        raise HeadlessTransitionError(
            "Boss cash-out does not yet own negative-money economy semantics"
        )
    if score < requirement:
        raise HeadlessTransitionError("cannot cash out an uncleared Boss Blind")

    supported_joker_types = (
        *_ROUND_END_INERT_JOKER_TYPES,
        *_ROUND_END_DOLLAR_JOKER_TYPES,
    )
    unsupported_jokers = [
        type(joker).__name__
        for joker in state.jokers
        if type(joker) not in supported_joker_types
    ]
    if unsupported_jokers:
        raise HeadlessTransitionError(
            "Boss cash-out does not yet own end-of-round Joker effects: "
            + ", ".join(unsupported_jokers)
        )
    if state.vouchers:
        raise HeadlessTransitionError(
            "Boss cash-out does not yet own Voucher economy modifiers"
        )
    if run.tags:
        raise HeadlessTransitionError(
            "Boss cash-out does not yet own tag cash-out effects"
        )
    if state.shop_active or any(
        (
            state.shop_jokers,
            state.shop_consumables,
            state.shop_boosters,
            state.shop_vouchers,
        )
    ):
        raise HeadlessTransitionError("Boss cash-out requires an ungenerated shop boundary")

    # Compute payout inputs against the pre-defeat public economy state. The Boss
    # reset must not erase the reward row before it is captured.
    interest = baseline_interest_dollars(money)
    joker_dollars = _round_end_joker_dollars(run)
    payout = reward + hands_remaining + joker_dollars + interest

    defeated = defeat_supported_boss(run)
    next_run = repopulate_round_end_deck(defeated)
    next_state = next_run.public
    next_state.money = money + payout
    next_state.phase = "SHOP"
    next_state.shop_active = True
    next_state.shop_jokers.clear()
    next_state.shop_consumables.clear()
    next_state.shop_boosters.clear()
    next_state.shop_vouchers.clear()
    return next_run
