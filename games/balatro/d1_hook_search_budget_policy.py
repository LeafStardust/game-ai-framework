from __future__ import annotations

"""Bound active-Hook D1 search without weakening ordinary blind search.

Live Red/White evidence showed two distinct Hook-specific latency failures. First,
a reserved player-discard root candidate could overrun before adaptive node 1; the
root-discard reserve now excludes active Hook. After that repair, canonical Hook
adaptive search still consumed essentially the full configured D1 budget on every
hand while producing no completed root. This guard gives active Hook a shorter
search window so the existing bounded structural timeout recovery can take over.

The cap is temporary for one decision and the configured engine budget is restored
immediately afterwards. Disabled Hook and every other blind keep the configured
budget unchanged.
"""

from games.balatro.d1_root_discard_reserve_policy import _active_hook
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


_HOOK_MAX_SEARCH_SECONDS = 3.0


def _decide_with_hook_search_cap(original_decide, self, state):
    configured = getattr(self, "max_search_seconds", None)
    if not _active_hook(state) or configured is None:
        return original_decide(self, state)

    bounded = min(float(configured), _HOOK_MAX_SEARCH_SECONDS)
    if bounded >= float(configured):
        return original_decide(self, state)

    self.max_search_seconds = bounded
    try:
        return original_decide(self, state)
    finally:
        self.max_search_seconds = configured


def install_d1_hook_search_budget_policy() -> None:
    if getattr(LiveHandActionDecisionEngine, "_hook_search_budget_installed", False):
        return

    original_decide = LiveHandActionDecisionEngine.decide

    def decide(self, state):
        return _decide_with_hook_search_cap(original_decide, self, state)

    LiveHandActionDecisionEngine.decide = decide
    LiveHandActionDecisionEngine._hook_search_budget_installed = True
