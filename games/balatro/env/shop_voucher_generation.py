"""Exact normal ``get_next_voucher_key(false)`` selection primitive.

Vanilla obtains an authoritative source-position pool from
``get_current_pool('Voucher')``. Every original Voucher position remains present
as either its center key or ``UNAVAILABLE``. If every original position is
unavailable, pinned vanilla's generic empty-pool fallback appends ``j_joker``.
That pathological non-Voucher result is outside the exact normal Voucher shop
publication boundary here, so an all-ineligible observed catalogue fails closed
*before* RNG advances rather than inventing ``v_blank``.

Normal run Voucher selection performs ``pseudorandom_element`` with
``pseudoseed('Voucher')`` and retries unavailable positions with
``Voucher_resample2``, ``Voucher_resample3``, etc. Voucher Tag deliberately uses
the different ``Voucher_fromtag`` key and is outside this boundary.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_UNAVAILABLE = "UNAVAILABLE"
_NORMAL_POOL_KEY = "Voucher"
_OBSERVED_RECORD_FIELDS = {
    "key",
    "cost",
    "unlocked",
    "requires",
    "no_pool_flag",
    "yes_pool_flag",
    "eligible",
}


@dataclass(frozen=True)
class NormalVoucherPoll:
    run: HeadlessRunState
    center_key: str
    resamples: int


def _validated_voucher_pool(pool: Sequence[str]) -> tuple[str, ...]:
    if isinstance(pool, (str, bytes)) or not isinstance(pool, Sequence):
        raise HeadlessTransitionError("authoritative Voucher pool must be a sequence")
    if not pool:
        raise HeadlessTransitionError("authoritative Voucher pool cannot be empty")

    result: list[str] = []
    available = 0
    seen: set[str] = set()
    for value in pool:
        if not isinstance(value, str) or not value:
            raise HeadlessTransitionError("Voucher pool positions must be nonempty strings")
        if value == _UNAVAILABLE:
            result.append(value)
            continue
        if not value.startswith("v_"):
            raise HeadlessTransitionError("Voucher pool contains a non-Voucher center key")
        if value in seen:
            raise HeadlessTransitionError("Voucher pool contains duplicate available center keys")
        seen.add(value)
        available += 1
        result.append(value)

    # Pinned vanilla falls through the generic empty-pool fallback to ``j_joker``.
    # The normal Voucher shop surface cannot exact-publish that non-Voucher center,
    # so reject rather than looping forever or substituting a fabricated Voucher.
    if available == 0:
        raise HeadlessTransitionError(
            "Voucher pool must contain an available/fallback center; "
            "all-ineligible input requires vanilla j_joker fallback"
        )
    return tuple(result)


def voucher_pool_from_observed_state(run: HeadlessRunState) -> tuple[str, ...]:
    """Build vanilla Voucher/UNAVAILABLE positions from canonical public state.

    Validation is deliberately complete before callers copy or advance RNG. A
    malformed, missing, partial or all-ineligible catalogue is therefore a
    zero-side-effect failure boundary.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.voucher_generation_pool_observed is not True:
        raise HeadlessTransitionError("authoritative Voucher generation pool is unobserved")
    records = state.voucher_generation_pool
    if not isinstance(records, list) or not records:
        raise HeadlessTransitionError("authoritative Voucher generation pool is empty")

    positions: list[str] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != _OBSERVED_RECORD_FIELDS:
            raise HeadlessTransitionError("Voucher generation catalogue record is malformed")
        key = record.get("key")
        if not isinstance(key, str) or not key.startswith("v_") or key in seen:
            raise HeadlessTransitionError("Voucher generation catalogue key is invalid")
        seen.add(key)
        cost = record.get("cost")
        if type(cost) is not int or cost < 0:
            raise HeadlessTransitionError("Voucher generation catalogue cost is invalid")
        unlocked = record.get("unlocked")
        if unlocked is not None and not isinstance(unlocked, bool):
            raise HeadlessTransitionError("Voucher generation catalogue unlock state is invalid")
        requires = record.get("requires")
        if not isinstance(requires, list):
            raise HeadlessTransitionError("Voucher generation catalogue requirements are invalid")
        if any(not isinstance(value, str) or not value.startswith("v_") for value in requires):
            raise HeadlessTransitionError("Voucher generation catalogue requirement key is invalid")
        if len(requires) != len(set(requires)):
            raise HeadlessTransitionError("Voucher generation catalogue requirements contain duplicates")
        for field in ("no_pool_flag", "yes_pool_flag"):
            value = record.get(field)
            if value is not None and (not isinstance(value, str) or not value):
                raise HeadlessTransitionError("Voucher generation catalogue pool flag is invalid")
        eligible = record.get("eligible")
        if not isinstance(eligible, bool):
            raise HeadlessTransitionError("Voucher generation catalogue eligibility is invalid")
        positions.append(key if eligible else _UNAVAILABLE)

    return _validated_voucher_pool(positions)


def poll_normal_voucher_key(
    run: HeadlessRunState,
    pool: Sequence[str],
) -> NormalVoucherPoll:
    """Select the exact normal current-round Voucher from a canonical source pool."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    validated = _validated_voucher_pool(pool)

    # Validate before copying/advancing RNG so malformed observed catalogues are
    # a zero-side-effect failure boundary.
    next_run = run.copy()
    index = next_run.rng.pseudorandom_element_index(len(validated), _NORMAL_POOL_KEY)
    center = validated[index]
    source_it = 1
    resamples = 0
    while center == _UNAVAILABLE:
        source_it += 1
        resamples += 1
        index = next_run.rng.pseudorandom_element_index(
            len(validated),
            f"{_NORMAL_POOL_KEY}_resample{source_it}",
        )
        center = validated[index]

    return NormalVoucherPoll(
        run=next_run,
        center_key=center,
        resamples=resamples,
    )


def poll_observed_normal_voucher_key(run: HeadlessRunState) -> NormalVoucherPoll:
    """Select a normal Voucher directly from the strict observed catalogue."""
    return poll_normal_voucher_key(run, voucher_pool_from_observed_state(run))
