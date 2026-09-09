"""Public-information-safe strategic transition evidence for Phase R5.

Strategic evidence reuses the frozen R3 ``EnvAction`` wrapper and canonical
production action identifiers. Simulator-private RNG state, physical draw order,
and retained zone authority never cross this public parity boundary.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.env.actions import EnvAction
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.shop_reroll import PaidBaseShopReroll, reroll_base_main_shop
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class PublicStrategicTransitionEvidence:
    """One frozen public pre-action/action/post-action strategic transition."""

    before: BalatroState
    action: EnvAction
    after: BalatroState


def _isolated_public_snapshot(state: BalatroState) -> BalatroState:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    return deepcopy(public_observation_state(state))


def build_public_strategic_transition_evidence(
    before_state: BalatroState,
    action: EnvAction,
    after_state: BalatroState,
) -> PublicStrategicTransitionEvidence:
    """Freeze one strategic transition at the canonical public-state boundary."""
    if not isinstance(action, EnvAction):
        raise TypeError("action must be EnvAction")
    # Resolving action_id here proves the evidence still points at a supported,
    # frozen production action rather than an arbitrary learner-only alias.
    action.action_id
    return PublicStrategicTransitionEvidence(
        before=_isolated_public_snapshot(before_state),
        action=action,
        after=_isolated_public_snapshot(after_state),
    )


def reroll_shop_with_public_evidence(
    run: HeadlessRunState,
) -> tuple[PaidBaseShopReroll, PublicStrategicTransitionEvidence]:
    """Execute the exact ordinary paid-reroll owner and capture public R5 evidence.

    This is evidence composition only. ``reroll_base_main_shop`` remains the sole
    mechanics owner and retains all private RNG authority on the returned run.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    action = EnvAction.from_alias("REROLL_SHOP")
    before = run.public
    result = reroll_base_main_shop(run)
    evidence = build_public_strategic_transition_evidence(
        before,
        action,
        result.run.public,
    )
    return result, evidence


def buy_joker_with_public_evidence(
    run: HeadlessRunState,
    *,
    slot: int,
) -> tuple[HeadlessRunState, PublicStrategicTransitionEvidence]:
    """Execute the canonical exact Joker-purchase owner and capture R5 evidence."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if isinstance(slot, bool) or not isinstance(slot, int):
        raise TypeError("slot must be an integer")
    action = EnvAction.from_alias("BUY_JOKER", {"slot": slot})
    before = run.public
    result = ShopTransitionEngine().step(run, action)
    evidence = build_public_strategic_transition_evidence(
        before,
        action,
        result.public,
    )
    return result, evidence


def buy_voucher_with_public_evidence(
    run: HeadlessRunState,
    *,
    slot: int,
) -> tuple[HeadlessRunState, PublicStrategicTransitionEvidence]:
    """Execute the canonical exact Voucher-redemption owner and capture R5 evidence."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if isinstance(slot, bool) or not isinstance(slot, int):
        raise TypeError("slot must be an integer")
    action = EnvAction.from_alias("BUY_VOUCHER", {"slot": slot})
    before = run.public
    result = ShopTransitionEngine().step(run, action)
    evidence = build_public_strategic_transition_evidence(
        before,
        action,
        result.public,
    )
    return result, evidence


def select_blind_with_public_evidence(
    run: HeadlessRunState,
) -> tuple[HeadlessRunState, PublicStrategicTransitionEvidence]:
    """Execute the canonical exact blind-start owner and capture R5 evidence."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    action = EnvAction.from_alias("SELECT_BLIND")
    before = run.public
    result = select_blind_exact(run)
    evidence = build_public_strategic_transition_evidence(
        before,
        action,
        result.public,
    )
    return result, evidence
