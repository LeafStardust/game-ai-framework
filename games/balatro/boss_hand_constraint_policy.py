from __future__ import annotations

"""Hard public boss constraints for D1 hand admission.

The Eye cannot repeat poker-hand types during the current blind. That restriction is
safe to enforce before strategy-aware ranking when an unused legal type exists.

The Psychic is deliberately not filtered here: Balatro accepts plays containing fewer
than five cards; such a hand simply does not score. Those plays can still be useful as
deliberate hand-burning/milling actions, so legality and score semantics must remain
separate.
"""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _hand_type(policy, plan) -> str:
    return str(policy._hand_evaluator.evaluate(list(plan.action.cards)).value).upper()


def _psychic_filter(state, plans):
    """Compatibility no-op: Psychic short plays are legal actions in Balatro."""
    return tuple(plans)


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
    # not observed. Do not use lifetime run counts.
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
        constrained = _eye_filter(self, state, plans)
        return original_decide(self, state, constrained, **kwargs)

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._boss_hand_constraints_installed = True
