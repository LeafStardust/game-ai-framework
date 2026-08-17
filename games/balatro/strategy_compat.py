from __future__ import annotations

from games.balatro.build.profile import PlaystyleIntent


class NeutralLegacyPlaystyleIntentTracker:
    """Compatibility bridge for the universal strategy-aware production path.

    v1.0's universal playbooks are the authoritative strategic signal. Some mature
    evaluators still accept the legacy playstyle-tracker interface for non-strategy
    mechanics such as held-card preservation or contextual scoring. Supplying this
    tracker keeps those mechanics while preventing the old Ante-5 lock from adding
    a second, competing strategy layer.
    """

    @property
    def locked(self) -> bool:
        return False

    def reset(self) -> None:
        return None

    def resolve(self, profile) -> PlaystyleIntent:
        del profile
        return PlaystyleIntent(strengths=(), locked=False, lock_ante=None)
