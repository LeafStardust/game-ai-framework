"""Exact ordinary blind-clear / cash-out transition for R2.

This module composes the already-owned round-end card-zone repopulation with the
Red Deck / White Stake economy slice whose vanilla semantics are exact. It stops
at an active, ungenerated SHOP; deterministic shop inventory generation remains a
separate owner.
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
from games.balatro.env.voucher_capabilities import (
    expected_base_reroll_cost_for_vouchers,
    expected_interest_cap_for_vouchers,
    expected_joker_edition_rate_for_vouchers,
    expected_planet_rate_for_vouchers,
    expected_shop_discount_percent_for_vouchers,
    expected_tarot_rate_for_vouchers,
    interest_cap_vouchers_are_exact,
    shop_generation_vouchers_are_exact,
    shop_pricing_vouchers_are_exact,
)
from games.balatro.joker import JokerContext
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.troubadour import TroubadourJoker


_BASE_INTEREST_AMOUNT = 1

_ROUND_END_INERT_JOKER_TYPES = (
    *_EXACT_R1_JOKER_ACQUISITION_TYPES,
    *_OWNED_DECK_SCORING_TYPES,
    StuntmanJoker,
    DrunkardJoker,
    TroubadourJoker,
    MerryAndyJoker,
)

_ROUND_END_DOLLAR_JOKER_TYPES = (
    GoldenJoker,
    Cloud9Joker,
    DelayedGratificationJoker,
)


def _require_exact_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HeadlessTransitionError(f"{name} must be an exact integer")
    return value


def baseline_interest_dollars(money: int, interest_cap: int = 25) -> int:
    """Return vanilla normal-mode interest from pre-payout current money."""
    money = _require_exact_int("money", money)
    interest_cap = _require_exact_int("interest_cap", interest_cap)
    if money < 0:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own negative-money economy semantics"
        )
    if interest_cap < 0:
        raise HeadlessTransitionError("interest_cap cannot be negative")
    if money < 5:
        return 0
    return _BASE_INTEREST_AMOUNT * min(money // 5, interest_cap // 5)


def _round_end_joker_dollars(run: HeadlessRunState) -> int:
    state = run.public
    total = 0
    for joker in state.jokers:
        if type(joker) not in _ROUND_END_DOLLAR_JOKER_TYPES:
            continue
        data: dict[str, object] = {}
        if type(joker) is Cloud9Joker:
            if state.owned_deck is None:
                raise HeadlessTransitionError(
                    "Cloud 9 cash-out requires authoritative owned_deck"
                )
            data["deck"] = state.owned_deck
        elif type(joker) is DelayedGratificationJoker:
            discards_used = _require_exact_int("discards_used", state.discards_used)
            discards_remaining = _require_exact_int(
                "discards_remaining", state.discards_remaining
            )
            if discards_used < 0:
                raise HeadlessTransitionError("discards_used cannot be negative")
            if discards_remaining < 0:
                raise HeadlessTransitionError("discards_remaining cannot be negative")
            data["discards_used"] = discards_used
            data["discards_remaining"] = discards_remaining
        context = JokerContext(state=state, trigger="ROUND_ENDED", data=data)
        joker.apply(context)
        total += _require_exact_int("Joker cash-out dollars", context.data.get("money", 0))
        total += _require_exact_int(
            "Joker cash-out dollars",
            context.data.get("delayed_gratification_money", 0),
        )
    return total


def _require_exact_voucher_shop_state(
    run: HeadlessRunState,
) -> tuple[int, float, float, float, int, int]:
    """Validate supported Voucher consequences needed at cash-out/shop entry."""
    state = run.public
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "ordinary cash-out does not own current Voucher generation modifiers"
        )
    if not shop_pricing_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "ordinary cash-out does not own current Voucher pricing modifiers"
        )
    if not interest_cap_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "ordinary cash-out does not own current Voucher interest-cap modifier"
        )

    discount = expected_shop_discount_percent_for_vouchers(state)
    edition = expected_joker_edition_rate_for_vouchers(state)
    tarot = expected_tarot_rate_for_vouchers(state)
    planet = expected_planet_rate_for_vouchers(state)
    base_reroll = expected_base_reroll_cost_for_vouchers(state)
    interest_cap = expected_interest_cap_for_vouchers(state)
    if any(
        value is None
        for value in (discount, edition, tarot, planet, base_reroll, interest_cap)
    ):
        raise HeadlessTransitionError("ordinary cash-out does not own Voucher consequences")
    if run.base_reroll_cost != base_reroll:
        raise HeadlessTransitionError(
            "persistent reroll cost does not match Voucher ownership"
        )
    if type(run.reroll_cost) is not int or run.reroll_cost < run.base_reroll_cost:
        raise HeadlessTransitionError(
            "ordinary cash-out does not own temporary/free reroll modifiers"
        )
    return (
        int(discount),
        float(edition),
        float(tarot),
        float(planet),
        int(base_reroll),
        int(interest_cap),
    )


def cash_out_baseline_ordinary_blind(run: HeadlessRunState) -> HeadlessRunState:
    """Cash out one exactly supported ordinary Red/White blind."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "ROUND_EVAL":
        raise HeadlessTransitionError("baseline cash-out requires ROUND_EVAL phase")
    if state.blind is None:
        raise HeadlessTransitionError("baseline cash-out requires an active blind")
    blind_type = getattr(state.blind, "type", None)
    if blind_type not in {BlindType.SMALL, BlindType.BIG}:
        raise HeadlessTransitionError(
            "baseline cash-out currently supports Small/Big blinds only"
        )

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
            "baseline cash-out does not yet own end-of-round Joker effects: "
            + ", ".join(unsupported_jokers)
        )
    if run.tags:
        raise HeadlessTransitionError(
            "baseline cash-out does not yet own tag cash-out effects"
        )

    discount, edition, tarot, planet, base_reroll, interest_cap = (
        _require_exact_voucher_shop_state(run)
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

    interest = baseline_interest_dollars(money, interest_cap)
    joker_dollars = _round_end_joker_dollars(run)
    payout = blind_reward + hands_remaining + joker_dollars + interest

    next_run = repopulate_round_end_deck(run)
    next_state = next_run.public
    next_state.money = money + payout
    next_state.phase = "SHOP"
    next_state.shop_active = True
    next_state.shop_inflation_observed = True
    next_state.shop_inflation = 0
    next_state.shop_discount_percent_observed = True
    next_state.shop_discount_percent = discount
    next_state.joker_generation_edition_rate = edition
    next_state.tarot_rate = tarot
    next_state.planet_rate = planet
    next_state.interest_cap = interest_cap
    if set(next_state.vouchers) & {"v_seed_money", "v_money_tree"}:
        next_state.interest_cap_observed = True

    next_run.base_reroll_cost = base_reroll
    next_run.reroll_cost = base_reroll

    next_state.shop_jokers.clear()
    next_state.shop_consumables.clear()
    next_state.shop_boosters.clear()
    next_state.shop_vouchers.clear()
    return next_run
