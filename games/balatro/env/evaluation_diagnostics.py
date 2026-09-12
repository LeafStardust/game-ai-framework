"""Authoritative per-episode diagnostics for frozen B0 evaluation evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from numbers import Real
from typing import Any, Iterable

from games.balatro.env.seeded_evaluation import (
    EVALUATION_DECK,
    EVALUATION_STAKE,
    FixedSeededEpisodeResult,
)
from games.balatro.env.state import EnvStateFrame, RunStatus
from games.balatro.env.unseeded_evaluation import UnseededEpisodeResult


EVALUATION_DIAGNOSTICS_SCHEMA = "balatro-b0-episode-diagnostics-v1"
FIXED_EVIDENCE_KIND = "FIXED_SEEDED"
UNSEEDED_EVIDENCE_KIND = "UNSEEDED"


class EvaluationDiagnosticsError(ValueError):
    """Raised when an exact diagnostic cannot be derived from episode state."""


def _exact_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvaluationDiagnosticsError(f"{name} must be an exact integer")
    if minimum is not None and value < minimum:
        raise EvaluationDiagnosticsError(f"{name} must be at least {minimum}")
    return value


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise EvaluationDiagnosticsError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise EvaluationDiagnosticsError(f"{name} must be finite")
    return result


def _result_provenance(
    result: FixedSeededEpisodeResult | UnseededEpisodeResult,
) -> tuple[str, str]:
    if isinstance(result, FixedSeededEpisodeResult):
        return FIXED_EVIDENCE_KIND, result.corpus_sha256
    if isinstance(result, UnseededEpisodeResult):
        return UNSEEDED_EVIDENCE_KIND, result.manifest_sha256
    raise TypeError("result must be a frozen B0 episode result")


@dataclass(frozen=True)
class EpisodeDiagnostics:
    schema_version: str
    evidence_kind: str
    evidence_sha256: str
    baseline_version: str
    episode_index: int
    game_seed: str
    status: RunStatus
    frame_count: int
    ante_reached: int
    ante_8_cleared: bool
    terminal_blind_score: float
    terminal_blind_requirement: float
    terminal_chip_margin: float
    terminal_requirement_progress: float
    starting_money: int
    minimum_money: int
    peak_money: int
    terminal_money: int

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_DIAGNOSTICS_SCHEMA:
            raise EvaluationDiagnosticsError("episode diagnostics schema version mismatch")
        if self.evidence_kind not in (FIXED_EVIDENCE_KIND, UNSEEDED_EVIDENCE_KIND):
            raise EvaluationDiagnosticsError("episode diagnostics evidence kind is invalid")
        if (
            not isinstance(self.evidence_sha256, str)
            or len(self.evidence_sha256) != 64
            or self.evidence_sha256 != self.evidence_sha256.lower()
            or any(character not in "0123456789abcdef" for character in self.evidence_sha256)
        ):
            raise EvaluationDiagnosticsError("episode diagnostics evidence digest is invalid")
        _exact_int(self.episode_index, "episode index", minimum=0)
        _exact_int(self.frame_count, "frame count", minimum=2)
        _exact_int(self.ante_reached, "ante reached", minimum=1)
        for name in ("starting_money", "minimum_money", "peak_money", "terminal_money"):
            _exact_int(getattr(self, name), name.replace("_", " "))
        if self.minimum_money > min(self.starting_money, self.terminal_money):
            raise EvaluationDiagnosticsError("minimum money is inconsistent")
        if self.peak_money < max(self.starting_money, self.terminal_money):
            raise EvaluationDiagnosticsError("peak money is inconsistent")
        if not isinstance(self.status, RunStatus) or not self.status.terminal:
            raise EvaluationDiagnosticsError("episode diagnostics require terminal status")
        if not isinstance(self.ante_8_cleared, bool):
            raise EvaluationDiagnosticsError("Ante 8 clear flag must be boolean")
        if self.ante_8_cleared != (self.status is RunStatus.ANTE_8_WIN):
            raise EvaluationDiagnosticsError("Ante 8 clear flag contradicts terminal status")
        if self.ante_8_cleared and self.ante_reached < 8:
            raise EvaluationDiagnosticsError("Ante 8 win did not reach Ante 8")
        score = _finite_number(self.terminal_blind_score, "terminal blind score")
        requirement = _finite_number(
            self.terminal_blind_requirement, "terminal blind requirement"
        )
        margin = _finite_number(self.terminal_chip_margin, "terminal chip margin")
        progress = _finite_number(
            self.terminal_requirement_progress, "terminal requirement progress"
        )
        if requirement <= 0.0:
            raise EvaluationDiagnosticsError("terminal blind requirement must be positive")
        if margin != score - requirement or progress != score / requirement:
            raise EvaluationDiagnosticsError("terminal survival diagnostics are inconsistent")

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def derive_episode_diagnostics(
    result: FixedSeededEpisodeResult | UnseededEpisodeResult,
    frames: Iterable[EnvStateFrame],
) -> EpisodeDiagnostics:
    """Derive exact diagnostics from a complete reset-to-terminal frame trace."""
    evidence_kind, evidence_sha256 = _result_provenance(result)
    trace = tuple(frames)
    if len(trace) < 2 or any(not isinstance(frame, EnvStateFrame) for frame in trace):
        raise EvaluationDiagnosticsError(
            "episode diagnostics require at least two authoritative frames"
        )
    first, terminal = trace[0], trace[-1]
    if result.action_count > len(trace) - 1:
        raise EvaluationDiagnosticsError("episode action count exceeds recorded transitions")
    if first.status is not RunStatus.RUNNING or first.state.phase != "BLIND_SELECT":
        raise EvaluationDiagnosticsError("episode trace must begin at the blind-select reset boundary")
    if _exact_int(first.state.ante, "initial ante", minimum=1) != 1:
        raise EvaluationDiagnosticsError("episode trace must begin at Ante 1")
    if any(frame.status.terminal for frame in trace[:-1]) or not terminal.status.terminal:
        raise EvaluationDiagnosticsError("episode trace must terminate exactly once at its final frame")
    if terminal.status is not result.status:
        raise EvaluationDiagnosticsError("episode trace terminal status mismatches result")

    antes: list[int] = []
    monies: list[int] = []
    for frame in trace:
        state = frame.state
        if (state.deck_name, state.stake_name) != (EVALUATION_DECK, EVALUATION_STAKE):
            raise EvaluationDiagnosticsError("episode trace is not Red Deck / White Stake")
        antes.append(_exact_int(state.ante, "frame ante", minimum=1))
        monies.append(_exact_int(state.money, "frame money"))
    if any(after < before for before, after in zip(antes, antes[1:])):
        raise EvaluationDiagnosticsError("episode trace ante progression cannot decrease")

    blind = terminal.state.blind
    if blind is None:
        raise EvaluationDiagnosticsError("terminal frame has no authoritative blind requirement")
    score = _finite_number(terminal.state.score, "terminal blind score")
    requirement = _finite_number(blind.requirement, "terminal blind requirement")
    if requirement <= 0.0:
        raise EvaluationDiagnosticsError("terminal blind requirement must be positive")
    ante_reached = max(antes)
    if result.status is RunStatus.ANTE_8_WIN and ante_reached < 8:
        raise EvaluationDiagnosticsError("Ante 8 win trace never reached Ante 8")
    if result.status is RunStatus.LOSS and score >= requirement:
        raise EvaluationDiagnosticsError("terminal loss already satisfies its blind requirement")
    if result.status is RunStatus.ANTE_8_WIN and score < requirement:
        raise EvaluationDiagnosticsError("Ante 8 win does not satisfy its blind requirement")

    return EpisodeDiagnostics(
        schema_version=EVALUATION_DIAGNOSTICS_SCHEMA,
        evidence_kind=evidence_kind,
        evidence_sha256=evidence_sha256,
        baseline_version=result.baseline_version,
        episode_index=result.episode_index,
        game_seed=result.game_seed,
        status=result.status,
        frame_count=len(trace),
        ante_reached=ante_reached,
        ante_8_cleared=result.status is RunStatus.ANTE_8_WIN,
        terminal_blind_score=score,
        terminal_blind_requirement=requirement,
        terminal_chip_margin=score - requirement,
        terminal_requirement_progress=score / requirement,
        starting_money=monies[0],
        minimum_money=min(monies),
        peak_money=max(monies),
        terminal_money=monies[-1],
    )
