from __future__ import annotations

"""Compatibility-only entry point for retired Joker-generation live-state setup.

Production observers explicitly compose Joker-generation public state through
``JokerGenerationPoolLiveMemoryObserver``. Importing this module must not mutate
the observer, translator, or ``BalatroState``.
"""

from games.balatro.live.joker_generation_pool_state import (
    JokerGenerationPoolLiveMemoryObserver,
    observe_joker_generation_state,
    reset_catalogue_cache,
)


__all__ = (
    "JokerGenerationPoolLiveMemoryObserver",
    "observe_joker_generation_state",
    "reset_catalogue_cache",
    "install_joker_generation_pool_live_state_policy",
)


def install_joker_generation_pool_live_state_policy() -> None:
    return None
