from __future__ import annotations

"""Per-decision cache for canonical Bond hand intents.

Live calibration showed 60-69 second D1 wall times while the bounded search itself
finished in ~4-5 seconds. The excess time came from repeatedly recomputing the full
Bond composition through `_strategy_fit` ranking/tie-break calls. A public state is
immutable for one D1 decision, so its Bond hand intents are safe to compute once and
reuse until that decision returns.
"""

from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def install_bond_d1_cache_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_bond_d1_cache_policy_installed", False):
        return

    original_hand_bond_intents = StrategyAwareLiveHandActionPolicy._hand_bond_intents
    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def hand_bond_intents(self, state):
        if getattr(self, "_bond_d1_cached_state_id", None) == id(state):
            cached = getattr(self, "_bond_d1_cached_intents", None)
            if cached is not None:
                return list(cached)
        return original_hand_bond_intents(self, state)

    def decide(self, state, plans, **kwargs):
        # Compute before marking the state cached so the original implementation is
        # called exactly once. All nested/tie-break accesses during this decision
        # then read the immutable tuple instead of re-running composition analysis.
        intents = tuple(original_hand_bond_intents(self, state))
        self._bond_d1_cached_state_id = id(state)
        self._bond_d1_cached_intents = intents
        try:
            return original_decide(self, state, plans, **kwargs)
        finally:
            self._bond_d1_cached_state_id = None
            self._bond_d1_cached_intents = None

    StrategyAwareLiveHandActionPolicy._hand_bond_intents = hand_bond_intents
    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._bond_d1_cache_policy_installed = True
