from __future__ import annotations

from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


def install_safe_pace_timeout_patch() -> None:
    """Keep timeout recovery structural without inventing discard intent.

    A wall-clock timeout is evidence only that D1 ran out of search budget. It is
    not evidence that discarding is better than playing, and it must never be used
    to fabricate a maximum-width discard. Completed search recommendations are
    preserved by the normal D1/log-resilience path; when no recommendation exists,
    delegate to the engine's original bounded structural fallback.
    """

    if getattr(LiveHandActionDecisionEngine, "_safe_pace_timeout_installed", False):
        return

    original = LiveHandActionDecisionEngine._structural_timeout_fallback

    def fallback(self, state, *, search_attempts):
        return original(self, state, search_attempts=search_attempts)

    LiveHandActionDecisionEngine._structural_timeout_fallback = fallback
    LiveHandActionDecisionEngine._safe_pace_timeout_installed = True
