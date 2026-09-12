"""Frozen paired seed corpus and result contract for B0 baseline evaluation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any

from games.balatro.env.action_encoding import PUBLIC_ACTION_VERSION
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.state import RunStatus
from games.balatro.env.symbolic_baseline import SYMBOLIC_HEADLESS_BASELINE_VERSION


FIXED_SEEDED_CORPUS_VERSION = "balatro-red-white-fixed-seeds-v1"
FIXED_SEEDED_CORPUS_SHA256 = (
    "ac4efb0beac9e9d14e09cdea7246cbc5c27150479f3ee2a3d93893d314a14ef7"
)
FIXED_SEEDED_EVALUATION_SCHEMA = "balatro-b0-fixed-seeded-evaluation-v1"
FIXED_SEEDED_EPISODE_COUNT = 64
EVALUATION_DECK = "RED"
EVALUATION_STAKE = "WHITE"
EVALUATION_MODE = "NORMAL"
EVALUATED_BASELINE_VERSIONS = (
    RANDOM_LEGAL_BASELINE_VERSION,
    SYMBOLIC_HEADLESS_BASELINE_VERSION,
)


class FixedSeededEvaluationError(ValueError):
    """Raised when fixed evaluation evidence is incomplete or has drifted."""


def _fixed_token(kind: str, index: int, length: int) -> str:
    payload = f"{FIXED_SEEDED_CORPUS_VERSION}\0{kind}\0{index}".encode("ascii")
    return sha256(payload).hexdigest()[:length].upper()


@dataclass(frozen=True)
class FixedSeededEpisodeSpec:
    corpus_version: str
    episode_index: int
    game_seed: str
    random_policy_seed: str

    def policy_seed(self, baseline_version: str) -> str | None:
        if baseline_version == RANDOM_LEGAL_BASELINE_VERSION:
            return self.random_policy_seed
        if baseline_version == SYMBOLIC_HEADLESS_BASELINE_VERSION:
            return None
        raise FixedSeededEvaluationError(
            f"unsupported baseline version: {baseline_version!r}"
        )


FIXED_SEEDED_EPISODES = tuple(
    FixedSeededEpisodeSpec(
        corpus_version=FIXED_SEEDED_CORPUS_VERSION,
        episode_index=index,
        game_seed=_fixed_token("game", index, 8),
        random_policy_seed=_fixed_token("random-policy", index, 16),
    )
    for index in range(FIXED_SEEDED_EPISODE_COUNT)
)
_generated_corpus_digest = sha256(
    "".join(
        f"{spec.episode_index}:{spec.game_seed}:{spec.random_policy_seed}\n"
        for spec in FIXED_SEEDED_EPISODES
    ).encode("ascii")
).hexdigest()
if _generated_corpus_digest != FIXED_SEEDED_CORPUS_SHA256:
    raise RuntimeError("fixed seeded evaluation corpus has drifted without a version bump")


def _require_spec(index: int) -> FixedSeededEpisodeSpec:
    if isinstance(index, bool) or not isinstance(index, int):
        raise FixedSeededEvaluationError("episode index must be an exact integer")
    if index < 0 or index >= len(FIXED_SEEDED_EPISODES):
        raise FixedSeededEvaluationError("episode index is outside the fixed corpus")
    return FIXED_SEEDED_EPISODES[index]


@dataclass(frozen=True)
class FixedSeededEpisodeResult:
    """Provenance and terminal outcome for one policy/corpus pairing."""

    schema_version: str
    corpus_version: str
    corpus_sha256: str
    baseline_version: str
    observation_version: str
    action_version: str
    deck: str
    stake: str
    mode: str
    episode_index: int
    game_seed: str
    policy_seed: str | None
    status: RunStatus
    action_count: int

    def __post_init__(self) -> None:
        if self.schema_version != FIXED_SEEDED_EVALUATION_SCHEMA:
            raise FixedSeededEvaluationError("evaluation result schema version mismatch")
        if self.corpus_version != FIXED_SEEDED_CORPUS_VERSION:
            raise FixedSeededEvaluationError("evaluation seed corpus version mismatch")
        if self.corpus_sha256 != FIXED_SEEDED_CORPUS_SHA256:
            raise FixedSeededEvaluationError("evaluation seed corpus digest mismatch")
        if self.baseline_version not in EVALUATED_BASELINE_VERSIONS:
            raise FixedSeededEvaluationError("evaluation result has an unsupported baseline")
        if self.observation_version != PUBLIC_OBSERVATION_VERSION:
            raise FixedSeededEvaluationError("evaluation observation version mismatch")
        if self.action_version != PUBLIC_ACTION_VERSION:
            raise FixedSeededEvaluationError("evaluation action version mismatch")
        if (self.deck, self.stake, self.mode) != (
            EVALUATION_DECK,
            EVALUATION_STAKE,
            EVALUATION_MODE,
        ):
            raise FixedSeededEvaluationError(
                "evaluation result is not Red Deck / White Stake / normal mode"
            )

        spec = _require_spec(self.episode_index)
        if self.game_seed != spec.game_seed:
            raise FixedSeededEvaluationError("evaluation game seed provenance mismatch")
        if self.policy_seed != spec.policy_seed(self.baseline_version):
            raise FixedSeededEvaluationError("evaluation policy seed provenance mismatch")
        if not isinstance(self.status, RunStatus) or not self.status.terminal:
            raise FixedSeededEvaluationError("evaluation result must be a terminal run status")
        if (
            isinstance(self.action_count, bool)
            or not isinstance(self.action_count, int)
            or self.action_count < 0
        ):
            raise FixedSeededEvaluationError(
                "evaluation action count must be a nonnegative exact integer"
            )

    @classmethod
    def completed(
        cls,
        *,
        baseline_version: str,
        episode_index: int,
        game_seed: str,
        policy_seed: str | None,
        status: RunStatus,
        action_count: int,
    ) -> "FixedSeededEpisodeResult":
        return cls(
            schema_version=FIXED_SEEDED_EVALUATION_SCHEMA,
            corpus_version=FIXED_SEEDED_CORPUS_VERSION,
            corpus_sha256=FIXED_SEEDED_CORPUS_SHA256,
            baseline_version=baseline_version,
            observation_version=PUBLIC_OBSERVATION_VERSION,
            action_version=PUBLIC_ACTION_VERSION,
            deck=EVALUATION_DECK,
            stake=EVALUATION_STAKE,
            mode=EVALUATION_MODE,
            episode_index=episode_index,
            game_seed=game_seed,
            policy_seed=policy_seed,
            status=status,
            action_count=action_count,
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(frozen=True)
class FixedSeededEvaluationReport:
    """Complete, canonically ordered evidence for both frozen baselines."""

    schema_version: str
    corpus_version: str
    corpus_sha256: str
    episodes: tuple[FixedSeededEpisodeResult, ...]

    def __post_init__(self) -> None:
        if self.schema_version != FIXED_SEEDED_EVALUATION_SCHEMA:
            raise FixedSeededEvaluationError("evaluation report schema version mismatch")
        if self.corpus_version != FIXED_SEEDED_CORPUS_VERSION:
            raise FixedSeededEvaluationError("evaluation report corpus version mismatch")
        if self.corpus_sha256 != FIXED_SEEDED_CORPUS_SHA256:
            raise FixedSeededEvaluationError("evaluation report corpus digest mismatch")
        if not isinstance(self.episodes, tuple):
            raise FixedSeededEvaluationError("evaluation report episodes must be a tuple")
        if any(not isinstance(episode, FixedSeededEpisodeResult) for episode in self.episodes):
            raise FixedSeededEvaluationError(
                "evaluation report contains an invalid episode result"
            )

        expected = tuple(
            (baseline, spec.episode_index, spec.game_seed, spec.policy_seed(baseline))
            for baseline in EVALUATED_BASELINE_VERSIONS
            for spec in FIXED_SEEDED_EPISODES
        )
        actual = tuple(
            (
                episode.baseline_version,
                episode.episode_index,
                episode.game_seed,
                episode.policy_seed,
            )
            for episode in self.episodes
        )
        if actual != expected:
            raise FixedSeededEvaluationError(
                "evaluation report must contain each fixed seed once per baseline in canonical order"
            )

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "corpus_version": self.corpus_version,
            "corpus_sha256": self.corpus_sha256,
            "episodes": [episode.as_dict() for episode in self.episodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


EpisodeExecutor = Callable[
    [str, FixedSeededEpisodeSpec, str | None],
    FixedSeededEpisodeResult,
]


def run_fixed_seeded_evaluation(
    execute_episode: EpisodeExecutor,
) -> FixedSeededEvaluationReport:
    """Execute the complete paired schedule through a supplied exact backend.

    This owner fixes scheduling and provenance only. The executor must run the
    actual deterministic episode and return a terminal result; no terminal
    outcome, unsupported mechanic, or missing episode is approximated here.
    """
    if not callable(execute_episode):
        raise TypeError("episode executor must be callable")

    results: list[FixedSeededEpisodeResult] = []
    for baseline_version in EVALUATED_BASELINE_VERSIONS:
        for spec in FIXED_SEEDED_EPISODES:
            result = execute_episode(
                baseline_version,
                spec,
                spec.policy_seed(baseline_version),
            )
            if not isinstance(result, FixedSeededEpisodeResult):
                raise TypeError("episode executor must return FixedSeededEpisodeResult")
            results.append(result)

    return FixedSeededEvaluationReport(
        schema_version=FIXED_SEEDED_EVALUATION_SCHEMA,
        corpus_version=FIXED_SEEDED_CORPUS_VERSION,
        corpus_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episodes=tuple(results),
    )
