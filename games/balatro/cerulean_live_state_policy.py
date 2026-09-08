from __future__ import annotations

"""Compatibility surface for native Cerulean Bell live-state observation.

The authoritative process-memory observer now exposes the public
``ability.forced_selection`` flag directly, and the canonical state translator
hydrates it onto ``BalatroCard.forced_selection``. No installation-time mutation is
required.
"""


def install_cerulean_live_state_policy() -> None:
    """Compatibility no-op; Cerulean live-state ownership is native."""
    return None
