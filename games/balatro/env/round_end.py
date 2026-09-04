"""Exact baseline blind-clear / cash-out transition for R2.9.

This module composes the already-owned round-end card-zone repopulation with the
narrow Red Deck / White Stake economy slice whose vanilla semantics are exact.
It deliberately stops at *shop entry*: deterministic shop inventory generation
is a later R2 owner and must not be approximated here.

Supported boundary:

* an already-cleared Small or Big Blind at the round-evaluation/cash-out screen;
* only audited Jokers that are inert at end-of-round/cash-out;
* no tags or vouchers that can contribute dollars or modify interest;
* baseline interest: $1 per $5 of pre-payout money, capped at $5;
* blind reward plus $1 for each unused hand;
* exact permanent-card repopulation through :mod:`round_zones`;
* transition to an active but not-yet-generated SHOP.

Everything else fails closed.  In particular, Boss defeat, Joker dollar bonuses
or decay/counter lifecycles, Voucher/tag economy modifiers, negative-money
edge cases, and shop RNG are not silently folded into this helper.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.round_zones import repopulate_round_end_deck
from games.balatro.env.transition import (
    _EXACT_R1_JOKER_ACQUISITION_TYPES,
    _OWNED_DECK_SCORING_TYPES,
    HeadlessRunState,
    HeadlessTransitionError,
)
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.troubadour import TroubadourJoker


_BASE_INTEREST_AMOUNT = 1
_BASE_INTEREST_CAP = 25

# These identities have no vanilla end-of-round dollar, destruction, decay, or
# counter transition.  Resource-sensitive Jokers below mutate persistent/current
# capacities at acquisition/round start, not during cash-out; those effects are
# already installed in canonical state by their existing owners.
_ROUND_END_INERT_JOKER_TYPES = (
    *_EXACT_R1_JOKER_ACQUISITION_TYPES,
    *_OWNED_DECK_SCORING_TYPES,
    StuntmanJoker,
    DrunkardJoker,
    TroubadourJoker,
    MerryAndyJoker,
)


def _require_exact_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HeadlessTransitionError(f"{name} must be an exact integer")
    return value


def baseline_interest_dollars(money: int) -> int:
    """Return vanilla baseline interest from *pre-payout* current money."""
    money = _require_exact_int("money", money)
    if money < 0:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own negative-money economy semantics"
        )
    if money < 5:
        return 0
    return _BASE_INTEREST_AMOUNT * min(money // 5, _BASE_INTEREST_CAP // 5)


def cash_out_baseline_ordinary_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Cash out one exactly supported ordinary Red/White blind.

    The input represents vanilla's round-evaluation/cash-out boundary after the
    blind has been defeated but before rewards are installed into run money.
    The input snapshot is never mutated.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "ROUND_EVAL":
        raise HeadlessTransitionError(
            "baseline cash-out requires ROUND_EVAL phase"
        )
    if state.blind is None:
        raise HeadlessTransitionError("baseline cash-out requires an active blind")
    blind_type = getattr(state.blind, "type", None)
    if blind_type not in {BlindType.SMALL, BlindType.BIG}:
        raise HeadlessTransitionError(
            "baseline cash-out currently supports Small/Big blinds only"
        )
    if state.blind_is_boss:
        raise HeadlessTransitionError("baseline cash-out does not own Boss defeat")

    score = _require_exact_int("score", state.score)
    requirement = _require_exact_int(
        "blind requirement", getattr(state.blind, "requirement", None)
    )
    if requirement < 0:
        raise HeadlessTransitionError("blind requirement cannot be negative")
    if score < requirement:
        raise HeadlessTransitionError("cannot cash out an uncleared blind")

    money = _require_exact_int("money", state.money)
    if money < 0:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own negative-money economy semantics"
        )
    hands_remaining = _require_exact_int("hands_remaining", state.hands_remaining)
    if hands_remaining < 0:
        raise HeadlessTransitionError("hands_remaining cannot be negative")
    blind_reward = _require_exact_int(
        "blind reward", getattr(state.blind, "reward", None)
    )
    if blind_reward < 0:
        raise HeadlessTransitionError("blind reward cannot be negative")

    unsupported_jokers = [
        type(joker).__name__
        for joker in state.jokers
        if type(joker) not in _ROUND_END_INERT_JOKER_TYPES
    ]
    if unsupported_jokers:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own end-of-round Joker effects: "
            + ", ".join(unsupported_jokers)
        )
    if state.vouchers:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own Voucher economy modifiers"
        )
    if run.tags:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own tag cash-out effects"
        )

    if state.shop_active or any(
        (
            state.shop_jokers,
            state.shop_consumables,
            state.shop_boosters,
            state.shop_vouchers,
        )
    ):
        raise HeadlessTransitionError(
            "baseline cash-out requires an ungenerated shop boundary"
        )

    # Vanilla interest is evaluated against G.GAME.dollars before blind reward,
    # unused-hand dollars, interest, and other evaluation rows are paid.
    interest = baseline_interest_dollars(money)
    payout = blind_reward + hands_remaining + interest

    next_run = repopulate_round_end_deck(run)
    next_state = next_run.public
    next_state.money = money + payout
    next_state.phase = "SHOP"
    next_state.shop_active = True

    # Shop inventory generation is deliberately not part of this transition.
    # Keep the containers exact and empty until the R2 shop-RNG owner fills them.
    next_state.shop_jokers.clear()
    next_state.shop_consumables.clear()
    next_state.shop_boosters.clear()
    next_state.shop_vouchers.clear()

    return next_run
