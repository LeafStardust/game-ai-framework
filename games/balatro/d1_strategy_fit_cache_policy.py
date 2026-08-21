from __future__ import annotations

"""Bound repeated D1 strategy-catalog work within one settled checkpoint.

The latest five-run telemetry contained D1 decisions of 34s and 77s while the
adaptive planner itself reported only 2.5s and 1.1s respectively. Strategy-aware
post-search ranking repeatedly recomputed the full strategy catalogue for equivalent
candidate hands. This policy caches only deterministic public-state calculations for
the duration of one ``decide`` call; ranking semantics are unchanged.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _play_hand_key(policy, state, action):
    if action.name != PLAY_CARDS:
        return None
    try:
        hand_type = policy._hand_evaluator.evaluate(list(action.cards)).value
    except (AttributeError, TypeError, ValueError):
        return None
    return ("PLAY_HAND", str(hand_type).upper())


def _action_key(policy, state, action):
    hand_key = _play_hand_key(policy, state, action)
    if hand_key is not None:
        # Strategy fit for PLAY is a function of poker-hand type plus the owned
        # Joker/strategy state, not of which equivalent card instances made it.
        return hand_key
    return (
        str(getattr(action, "name", "")),
        tuple(id(card) for card in getattr(action, "cards", ()) or ()),
    )


def install_d1_strategy_fit_cache_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_five_run_strategy_fit_cache_installed", False):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide
    original_weights = StrategyAwareLiveHandActionPolicy._owned_joker_hand_weights
    original_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def decide(self, state, plans, **kwargs):
        self._checkpoint_strategy_fit_cache = {}
        self._checkpoint_owned_hand_weights = None
        self._checkpoint_strategy_fit_state_id = id(state)
        try:
            return original_decide(self, state, plans, **kwargs)
        finally:
            self._checkpoint_strategy_fit_cache = None
            self._checkpoint_owned_hand_weights = None
            self._checkpoint_strategy_fit_state_id = None

    def _owned_joker_hand_weights(self, state):
        if getattr(self, "_checkpoint_strategy_fit_state_id", None) == id(state):
            cached = getattr(self, "_checkpoint_owned_hand_weights", None)
            if cached is not None:
                return dict(cached)
            value = original_weights(self, state)
            self._checkpoint_owned_hand_weights = dict(value)
            return value
        return original_weights(self, state)

    def _strategy_fit(self, state, action):
        cache = getattr(self, "_checkpoint_strategy_fit_cache", None)
        if (
            cache is None
            or getattr(self, "_checkpoint_strategy_fit_state_id", None) != id(state)
        ):
            return original_fit(self, state, action)
        key = _action_key(self, state, action)
        if key in cache:
            return cache[key]
        value = original_fit(self, state, action)
        cache[key] = value
        return value

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._owned_joker_hand_weights = _owned_joker_hand_weights
    StrategyAwareLiveHandActionPolicy._strategy_fit = _strategy_fit
    StrategyAwareLiveHandActionPolicy._five_run_strategy_fit_cache_installed = True
