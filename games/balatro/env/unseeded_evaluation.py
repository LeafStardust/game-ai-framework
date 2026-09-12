"""Fresh paired-seed manifests and evidence contract for B0 evaluation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from secrets import token_bytes
from typing import Any

from games.balatro.env.action_encoding import PUBLIC_ACTION_VERSION
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    EVALUATION_DECK,
    EVALUATION_MODE,
    EVALUATION_STAKE,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.state import RunStatus
from games.balatro.env.symbolic_baseline import SYMBOLIC_HEADLESS_BASELINE_VERSION


UNSEEDED_MANIFEST_SCHEMA = "balatro-red-white-unseeded-manifest-v1"
UNSEEDED_EVALUATION_SCHEMA = "balatro-b0-unseeded-evaluation-v1"
UNSEEDED_EPISODE_COUNT = 64
UNSEEDED_ENTROPY_BYTES = 32


class UnseededEvaluationError(ValueError):
    """Raised when fresh evaluation provenance or evidence is invalid."""


@dataclass(frozen=True)
class UnseededEpisodeSpec:
    episode_index: int
    game_seed: str
    random_policy_seed: str

    def policy_seed(self, baseline_version: str) -> str | None:
        if baseline_version == RANDOM_LEGAL_BASELINE_VERSION:
            return self.random_policy_seed
        if baseline_version == SYMBOLIC_HEADLESS_BASELINE_VERSION:
            return None
        raise UnseededEvaluationError(
            f"unsupported baseline version: {baseline_version!r}"
        )


def _derived_token(entropy_hex: str, kind: str, index: int, length: int) -> str:
    payload = f"{UNSEEDED_MANIFEST_SCHEMA}\0{entropy_hex}\0{kind}\0{index}".encode("ascii")
    return sha256(payload).hexdigest()[:length].upper()


def _derived_episodes(entropy_hex: str) -> tuple[UnseededEpisodeSpec, ...]:
    return tuple(
        UnseededEpisodeSpec(
            episode_index=index,
            game_seed=_derived_token(entropy_hex, "game", index, 8),
            random_policy_seed=_derived_token(entropy_hex, "random-policy", index, 16),
        )
        for index in range(UNSEEDED_EPISODE_COUNT)
    )


def _manifest_digest(
    entropy_hex: str,
    episodes: tuple[UnseededEpisodeSpec, ...],
) -> str:
    body = "".join(
        f"{spec.episode_index}:{spec.game_seed}:{spec.random_policy_seed}\n"
        for spec in episodes
    )
    return sha256(f"{UNSEEDED_MANIFEST_SCHEMA}\n{entropy_hex}\n{body}".encode("ascii")).hexdigest()


def _is_lower_hex(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class UnseededEvaluationManifest:
    """Replayable record of one freshly sampled evaluation schedule."""

    schema_version: str
    entropy_hex: str
    manifest_sha256: str
    episodes: tuple[UnseededEpisodeSpec, ...]

    def __post_init__(self) -> None:
        if self.schema_version != UNSEEDED_MANIFEST_SCHEMA:
            raise UnseededEvaluationError("unseeded manifest schema version mismatch")
        if not _is_lower_hex(self.entropy_hex, UNSEEDED_ENTROPY_BYTES * 2):
            raise UnseededEvaluationError("manifest entropy must be 32 bytes of lowercase hex")
        if not isinstance(self.episodes, tuple):
            raise UnseededEvaluationError("unseeded manifest episodes must be a tuple")
        expected = _derived_episodes(self.entropy_hex)
        if self.episodes != expected:
            raise UnseededEvaluationError("unseeded manifest seed derivation mismatch")
        if self.manifest_sha256 != _manifest_digest(self.entropy_hex, expected):
            raise UnseededEvaluationError("unseeded manifest digest mismatch")
        fixed_seeds = {spec.game_seed for spec in FIXED_SEEDED_EPISODES}
        game_seeds = [spec.game_seed for spec in self.episodes]
        policy_seeds = [spec.random_policy_seed for spec in self.episodes]
        if (
            len(set(game_seeds)) != UNSEEDED_EPISODE_COUNT
            or len(set(policy_seeds)) != UNSEEDED_EPISODE_COUNT
            or fixed_seeds.intersection(game_seeds)
        ):
            raise UnseededEvaluationError(
                "unseeded manifest seeds must be unique and separate from the fixed corpus"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entropy_hex": self.entropy_hex,
            "manifest_sha256": self.manifest_sha256,
            "episodes": [asdict(spec) for spec in self.episodes],
        }


EntropySource = Callable[[int], bytes]


def create_unseeded_evaluation_manifest(
    entropy_source: EntropySource = token_bytes,
) -> UnseededEvaluationManifest:
    if not callable(entropy_source):
        raise TypeError("entropy source must be callable")
    entropy = entropy_source(UNSEEDED_ENTROPY_BYTES)
    if not isinstance(entropy, bytes) or len(entropy) != UNSEEDED_ENTROPY_BYTES:
        raise UnseededEvaluationError("entropy source must return exactly 32 bytes")
    entropy_hex = entropy.hex()
    episodes = _derived_episodes(entropy_hex)
    return UnseededEvaluationManifest(
        schema_version=UNSEEDED_MANIFEST_SCHEMA,
        entropy_hex=entropy_hex,
        manifest_sha256=_manifest_digest(entropy_hex, episodes),
        episodes=episodes,
    )


@dataclass(frozen=True)
class UnseededEpisodeResult:
    schema_version: str
    manifest_entropy_hex: str
    manifest_sha256: str
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
        if self.schema_version != UNSEEDED_EVALUATION_SCHEMA:
            raise UnseededEvaluationError("unseeded result schema version mismatch")
        if not _is_lower_hex(self.manifest_entropy_hex, UNSEEDED_ENTROPY_BYTES * 2):
            raise UnseededEvaluationError("unseeded result manifest entropy is invalid")
        derived = _derived_episodes(self.manifest_entropy_hex)
        if self.manifest_sha256 != _manifest_digest(self.manifest_entropy_hex, derived):
            raise UnseededEvaluationError("unseeded result manifest digest mismatch")
        if self.baseline_version not in EVALUATED_BASELINE_VERSIONS:
            raise UnseededEvaluationError("unseeded result has an unsupported baseline")
        if self.observation_version != PUBLIC_OBSERVATION_VERSION:
            raise UnseededEvaluationError("unseeded result observation version mismatch")
        if self.action_version != PUBLIC_ACTION_VERSION:
            raise UnseededEvaluationError("unseeded result action version mismatch")
        if (self.deck, self.stake, self.mode) != (
            EVALUATION_DECK,
            EVALUATION_STAKE,
            EVALUATION_MODE,
        ):
            raise UnseededEvaluationError(
                "unseeded result is not Red Deck / White Stake / normal mode"
            )
        if isinstance(self.episode_index, bool) or not isinstance(self.episode_index, int):
            raise UnseededEvaluationError("unseeded episode index must be an exact integer")
        if self.episode_index < 0 or self.episode_index >= len(derived):
            raise UnseededEvaluationError("unseeded episode index is outside the manifest")
        spec = derived[self.episode_index]
        if self.game_seed != spec.game_seed:
            raise UnseededEvaluationError("unseeded game seed provenance mismatch")
        if self.policy_seed != spec.policy_seed(self.baseline_version):
            raise UnseededEvaluationError("unseeded policy seed provenance mismatch")
        if not isinstance(self.status, RunStatus) or not self.status.terminal:
            raise UnseededEvaluationError("unseeded result must be a terminal run status")
        if (
            isinstance(self.action_count, bool)
            or not isinstance(self.action_count, int)
            or self.action_count < 0
        ):
            raise UnseededEvaluationError(
                "unseeded action count must be a nonnegative exact integer"
            )

    @classmethod
    def completed(
        cls,
        manifest: UnseededEvaluationManifest,
        *,
        baseline_version: str,
        episode_index: int,
        game_seed: str,
        policy_seed: str | None,
        status: RunStatus,
        action_count: int,
    ) -> "UnseededEpisodeResult":
        if not isinstance(manifest, UnseededEvaluationManifest):
            raise TypeError("manifest must be UnseededEvaluationManifest")
        return cls(
            schema_version=UNSEEDED_EVALUATION_SCHEMA,
            manifest_entropy_hex=manifest.entropy_hex,
            manifest_sha256=manifest.manifest_sha256,
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
class UnseededEvaluationReport:
    schema_version: str
    manifest: UnseededEvaluationManifest
    episodes: tuple[UnseededEpisodeResult, ...]

    def __post_init__(self) -> None:
        if self.schema_version != UNSEEDED_EVALUATION_SCHEMA:
            raise UnseededEvaluationError("unseeded report schema version mismatch")
        if not isinstance(self.manifest, UnseededEvaluationManifest):
            raise UnseededEvaluationError("unseeded report manifest is invalid")
        if not isinstance(self.episodes, tuple) or any(
            not isinstance(episode, UnseededEpisodeResult) for episode in self.episodes
        ):
            raise UnseededEvaluationError("unseeded report episodes are invalid")
        expected = tuple(
            (
                self.manifest.manifest_sha256,
                self.manifest.entropy_hex,
                baseline,
                spec.episode_index,
                spec.game_seed,
                spec.policy_seed(baseline),
            )
            for baseline in EVALUATED_BASELINE_VERSIONS
            for spec in self.manifest.episodes
        )
        actual = tuple(
            (
                episode.manifest_sha256,
                episode.manifest_entropy_hex,
                episode.baseline_version,
                episode.episode_index,
                episode.game_seed,
                episode.policy_seed,
            )
            for episode in self.episodes
        )
        if actual != expected:
            raise UnseededEvaluationError(
                "unseeded report must contain each manifest seed once per baseline in canonical order"
            )

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest": self.manifest.as_dict(),
            "episodes": [episode.as_dict() for episode in self.episodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


EpisodeExecutor = Callable[
    [str, UnseededEpisodeSpec, str | None],
    UnseededEpisodeResult,
]


def run_unseeded_evaluation(
    manifest: UnseededEvaluationManifest,
    execute_episode: EpisodeExecutor,
) -> UnseededEvaluationReport:
    if not isinstance(manifest, UnseededEvaluationManifest):
        raise TypeError("manifest must be UnseededEvaluationManifest")
    if not callable(execute_episode):
        raise TypeError("episode executor must be callable")
    results: list[UnseededEpisodeResult] = []
    for baseline_version in EVALUATED_BASELINE_VERSIONS:
        for spec in manifest.episodes:
            result = execute_episode(
                baseline_version,
                spec,
                spec.policy_seed(baseline_version),
            )
            if not isinstance(result, UnseededEpisodeResult):
                raise TypeError("episode executor must return UnseededEpisodeResult")
            results.append(result)
    return UnseededEvaluationReport(
        schema_version=UNSEEDED_EVALUATION_SCHEMA,
        manifest=manifest,
        episodes=tuple(results),
    )
