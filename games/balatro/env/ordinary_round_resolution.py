"""Compose the owned ordinary-Blind win and cash-out lifecycle in source order."""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.blinds.blind import BlindType
from games.balatro.env.blind_progression import (
    BlindProgressionState,
    finalize_won_round_progression,
)
from games.balatro.env.round_end import cash_out_baseline_ordinary_blind
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


@dataclass(frozen=True)
class OrdinaryRoundResolution:
    """Exact successor at the active, ungenerated SHOP boundary."""

    run: HeadlessRunState
    progression: BlindProgressionState


def resolve_supported_ordinary_round(
    run: HeadlessRunState,
    progression: BlindProgressionState,
) -> OrdinaryRoundResolution:
    """Resolve a cleared Small/Big Blind through exact progression and cash-out.

    Inputs are never mutated. The result intentionally stops at the active,
    ungenerated SHOP produced by the cash-out owner; shop inventory generation
    remains a separate authority and must complete before this boundary can be
    exposed to a strategic policy.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")

    blind = run.public.blind
    blind_type = getattr(blind, "type", None)
    if blind_type not in {BlindType.SMALL, BlindType.BIG}:
        raise HeadlessTransitionError(
            "ordinary round resolution requires a Small or Big Blind"
        )

    progressed_run, progressed_state = finalize_won_round_progression(
        run,
        progression,
        blind_type=blind_type.value,
    )
    paid_run = cash_out_baseline_ordinary_blind(progressed_run)
    if paid_run.blind_progression_state != progressed_state:
        raise HeadlessTransitionError(
            "ordinary cash-out did not preserve retained blind progression"
        )
    return OrdinaryRoundResolution(
        run=paid_run,
        progression=progressed_state,
    )
