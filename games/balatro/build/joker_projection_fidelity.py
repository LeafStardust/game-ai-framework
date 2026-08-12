from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from games.balatro.live.joker_projection import LiveJokerScoreProjector

from .joker_live_state_fidelity import HYDRATED, JokerLiveStateFidelityAuditor


SUPPORTED = "SUPPORTED"
DEFERRED = "DEFERRED"
GAP = "GAP"
ERROR = "ERROR"


@dataclass(frozen=True)
class JokerProjectionFidelityEntry:
    module: str
    class_name: str
    status: str
    reason: str | None = None


@dataclass(frozen=True)
class JokerProjectionFidelityReport:
    entries: tuple[JokerProjectionFidelityEntry, ...]

    @property
    def counts(self) -> tuple[tuple[str, int], ...]:
        counts = Counter(entry.status for entry in self.entries)
        return tuple(sorted(counts.items()))

    @property
    def gaps(self) -> tuple[JokerProjectionFidelityEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status in {GAP, ERROR})

    def count(self, status: str) -> int:
        return dict(self.counts).get(status, 0)


class JokerProjectionFidelityAuditor:
    """Route every hydrated mutable Joker into runtime support or explicit deferral.

    The live-state fidelity audit proves that mutable model state can be restored
    from public observation. This audit proves a separate property: every hydrated
    class is deliberately classified for hypothetical score projection. A class is
    ``SUPPORTED`` only after its current event/score transition is validated;
    otherwise it must be explicitly ``DEFERRED``. Anything else is a ``GAP``.
    """

    def audit(self) -> JokerProjectionFidelityReport:
        live_report = JokerLiveStateFidelityAuditor().audit()
        hydrated_entries = [
            entry for entry in live_report.entries if entry.status == HYDRATED
        ]
        hydrated_names = {entry.class_name for entry in hydrated_entries}
        deferred_names = set(LiveJokerScoreProjector.DEFERRED_HYDRATED_CLASS_NAMES)

        entries: list[JokerProjectionFidelityEntry] = []
        for entry in hydrated_entries:
            class_name = entry.class_name
            if class_name in LiveJokerScoreProjector.SUPPORTED_CLASS_NAMES:
                status = SUPPORTED
                reason = None
            elif class_name in deferred_names:
                status = DEFERRED
                reason = LiveJokerScoreProjector.deferred_reason(class_name)
            else:
                status = GAP
                reason = "hydrated mutable Joker has no runtime projection classification"
            entries.append(
                JokerProjectionFidelityEntry(
                    module=entry.module,
                    class_name=class_name,
                    status=status,
                    reason=reason,
                )
            )

        # Explicit deferrals are a contract, not a graveyard. Flag stale names so a
        # rename/removal cannot leave the projection matrix looking complete.
        for class_name in sorted(deferred_names - hydrated_names):
            entries.append(
                JokerProjectionFidelityEntry(
                    module="<projection-contract>",
                    class_name=class_name,
                    status=ERROR,
                    reason="deferred runtime class is not hydrated mutable live state",
                )
            )

        return JokerProjectionFidelityReport(entries=tuple(entries))
