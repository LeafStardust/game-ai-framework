"""Exact normal ``get_next_voucher_key(false)`` selection primitive.

Vanilla obtains an authoritative source-position pool from
``get_current_pool('Voucher')``. Every original Voucher position remains present
as either its center key or ``UNAVAILABLE``; if every position is unavailable,
``get_current_pool`` replaces the pool with ``{'v_blank'}``.

Normal run Voucher selection then performs ``pseudorandom_element`` with
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

    # Source get_current_pool never returns an all-UNAVAILABLE Voucher pool: it
    # replaces an empty eligible pool with v_blank. Rejecting here prevents an
    # accidental infinite resample loop from malformed external state.
    if available == 0:
        raise HeadlessTransitionError(
            "Voucher pool must contain get_current_pool's available/fallback center"
        )
    return tuple(result)


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
