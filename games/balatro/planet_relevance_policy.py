from __future__ import annotations

"""Deprecated compatibility shim for the removed D4 Planet relevance wrapper.

Phase H4 moved Planet acquisition strategy into the canonical D4 owner through
projected StrategyDelta. The historical Bond-rank relevance veto is no longer a
production authority. Keep the installer symbol temporarily so stale imports do
not fail during migration cleanup, but it must never monkey-patch D4 again.
"""


def install_planet_relevance_policy() -> None:
    """Compatibility no-op; the legacy Planet relevance authority is retired."""
    return None
