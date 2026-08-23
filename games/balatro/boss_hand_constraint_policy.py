from __future__ import annotations

"""Hard public boss constraints for D1 hand admission.

These are not scoring preferences.  The Psychic rejects plays with fewer than five
cards, and The Eye rejects poker-hand types already used during the current blind.
Allowing such actions into ordinary D1 ranking makes projected score/pace misleading,
so remove them before the strategy-aware policy evaluates the plan set.
"""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _hand_type(policy, plan) -> str:
    return str(policy._hand_evaluator.evaluate(list(plan.action.cards)).value).upper()


def _psychic_filter(state, plans):
    if str(getattr(state, "boss_name", "") or "") != "The Psychic":
        return tuple(plans)
    if boss_blind_disabled_by_owned_jokers(state):
        return tuple(plans)

    supplied = tuple(plans)
    legal_plays = tuple(
        plan
        for plan in supplied
        if plan.action.name == PLAY_CARDS and len(tuple(plan.action.cards or ())) == 5
    )
    if not legal_plays:
        # Fail closed to the original planner if observation/action generation is
        # unexpectedly incomplete rather than manufacturing an illegal plan set.
        return supplied
    discards = tuple(plan for plan in supplied if plan.action.name == DISCARD_CARDS)
    return (*legal_plays, *discards)


def _eye_filter(policy, state, plans):
    if str(getattr(state, "boss_name", "") or "") != "The Eye":
        return tuple(plans)
    if boss_blind_disabled_by_owned_jokers(state):
        return tuple(plans)

    supplied = tuple(plans)
    used = {
        str(value).upper()
        for value in (getattr(state, "boss_blind_hands", set()) or set())
    }
    # Fall back to the public current-round counters when the blind-owned table was
    # not observed.  Do not use lifetime run counts.
    if not used and not bool(getattr(state, "boss_blind_state_observed", False)):
        used = {
            str(hand).upper()
            for hand, count in (getattr(state, "round_hand_play_counts", {}) or {}).items()
            if int(count or 0) > 0
        }

    if not used:
        return supplied

    unused_plays = tuple(
        plan
        for plan in supplied
        if plan.action.name == PLAY_CARDS and _hand_type(policy, plan) not in used
    )
    if not unused_plays:
        return supplied
    discards = tuple(plan for plan in supplied if plan.action.name == DISCARD_CARDS)
    return (*unused_plays, *discards)


def install_boss_hand_constraint_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_boss_hand_constraints_installed", False):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        constrained = _psychic_filter(state, plans)
        constrained = _eye_filter(self, state, constrained)
        return original_decide(self, state, constrained, **kwargs)

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._boss_hand_constraints_installed = True
