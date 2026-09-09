"""Coherent private R5 checkpoint for exact Economy-Tag blind-skip replay."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from games.balatro.env.actions import EnvAction
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.parity import (
    PublicStrategicParityComparison,
    compare_public_strategic_evidence,
)
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
    skip_blind_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.live.private_run_state import (
    LivePrivateRunStateError,
    active_tag_count_from_live_memory,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError
from games.balatro.live.translator import DefaultBalatroStateTranslator


class LiveBlindSkipParityCheckpointError(RuntimeError):
    """Raised when exact blind-skip replay authority is unavailable."""


@dataclass(frozen=True)
class LiveBlindSkipProgression:
    small_status: str
    big_status: str
    boss_status: str
    blind_on_deck: str
    blind_ante: int
    small_tag: str
    big_tag: str

    def to_headless(self) -> BlindProgressionState:
        return BlindProgressionState(
            small_status=self.small_status,
            big_status=self.big_status,
            boss_status=self.boss_status,
            blind_on_deck=self.blind_on_deck,
            blind_ante=self.blind_ante,
            small_tag=self.small_tag,
            big_tag=self.big_tag,
        )


@dataclass(frozen=True)
class LiveBlindSkipParityCheckpoint:
    public_snapshot: LiveBalatroSnapshot
    progression: LiveBlindSkipProgression
    active_tag_count: int
    skips: int


@dataclass(frozen=True)
class LiveBlindSkipReplayComparison:
    matches: bool
    differences: tuple[str, ...]
    public: PublicStrategicParityComparison
    simulator_evidence: PublicStrategicTransitionEvidence


def _table(decoder, value, *, field: str) -> dict[str, Any]:
    if value is None or getattr(value, "kind", None) != "table":
        raise LiveBlindSkipParityCheckpointError(f"{field} table is unavailable")
    try:
        return decoder.string_fields(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LiveBlindSkipParityCheckpointError(f"unable to read {field} table") from exc


def _string(value, *, field: str) -> str:
    if value is None or getattr(value, "kind", None) != "string":
        raise LiveBlindSkipParityCheckpointError(f"{field} must be an exact string")
    result = str(value.value).strip()
    if not result:
        raise LiveBlindSkipParityCheckpointError(f"{field} cannot be empty")
    return result


def _integer(value, *, field: str, minimum: int | None = None) -> int:
    if value is None or getattr(value, "kind", None) not in {"integer", "number"}:
        raise LiveBlindSkipParityCheckpointError(f"{field} must be an exact integer")
    raw = value.value
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not float(raw).is_integer():
        raise LiveBlindSkipParityCheckpointError(f"{field} must be an exact integer")
    result = int(raw)
    if minimum is not None and result < minimum:
        raise LiveBlindSkipParityCheckpointError(f"{field} is below its exact minimum")
    return result


def _progression_from_live_memory(decoder, root) -> tuple[LiveBlindSkipProgression, int]:
    game = _table(decoder, root.get("GAME"), field="G.GAME")
    resets = _table(decoder, game.get("round_resets"), field="G.GAME.round_resets")
    states = _table(decoder, resets.get("blind_states"), field="round_resets.blind_states")
    tags = _table(decoder, resets.get("blind_tags"), field="round_resets.blind_tags")
    progression = LiveBlindSkipProgression(
        small_status=_string(states.get("Small"), field="blind_states.Small"),
        big_status=_string(states.get("Big"), field="blind_states.Big"),
        boss_status=_string(states.get("Boss"), field="blind_states.Boss"),
        blind_on_deck=_string(game.get("blind_on_deck"), field="blind_on_deck"),
        blind_ante=_integer(resets.get("blind_ante"), field="blind_ante"),
        small_tag=_string(tags.get("Small"), field="blind_tags.Small"),
        big_tag=_string(tags.get("Big"), field="blind_tags.Big"),
    )
    try:
        progression.to_headless()
    except ValueError as exc:
        raise LiveBlindSkipParityCheckpointError(
            "live blind progression is not canonical"
        ) from exc
    skips = _integer(game.get("skips"), field="G.GAME.skips", minimum=0)
    return progression, skips


def capture_live_blind_skip_parity_checkpoint(observer) -> LiveBlindSkipParityCheckpoint:
    before = observer.observe()
    if not isinstance(before, LiveBalatroSnapshot):
        raise LiveBlindSkipParityCheckpointError("observer did not return LiveBalatroSnapshot")
    if before.phase != "BLIND_SELECT" or before.state_complete is not True:
        raise LiveBlindSkipParityCheckpointError(
            "blind-skip parity checkpoint requires complete BLIND_SELECT"
        )
    try:
        decoder, _, root = observer._root()
        progression, skips = _progression_from_live_memory(decoder, root)
        active_tag_count = active_tag_count_from_live_memory(decoder, root)
    except (LivePrivateRunStateError, OSError, RuntimeError) as exc:
        if isinstance(exc, LiveBlindSkipParityCheckpointError):
            raise
        raise LiveBlindSkipParityCheckpointError(
            "unable to capture exact live blind-skip replay authority"
        ) from exc
    after = observer.observe()
    if before != after:
        raise LiveBlindSkipParityCheckpointError(
            "live public state changed while capturing blind-skip replay authority"
        )
    return LiveBlindSkipParityCheckpoint(
        public_snapshot=deepcopy(before),
        progression=progression,
        active_tag_count=active_tag_count,
        skips=skips,
    )


def headless_blind_skip_run_from_live_checkpoint(
    checkpoint: LiveBlindSkipParityCheckpoint,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> HeadlessRunState:
    if not isinstance(checkpoint, LiveBlindSkipParityCheckpoint):
        raise TypeError("checkpoint must be LiveBlindSkipParityCheckpoint")
    if checkpoint.public_snapshot.phase != "BLIND_SELECT":
        raise LiveBlindSkipParityCheckpointError(
            "headless blind-skip restoration requires BLIND_SELECT checkpoint"
        )
    if checkpoint.active_tag_count != 0:
        raise LiveBlindSkipParityCheckpointError(
            "Economy-Tag blind-skip parity does not admit active Tags"
        )
    translator = translator or DefaultBalatroStateTranslator()
    public = translator.translate(checkpoint.public_snapshot)
    try:
        return HeadlessRunState(
            public=public,
            seed="R5-BLIND-SKIP-REPLAY",
            blind_progression_state=checkpoint.progression.to_headless(),
            skips=checkpoint.skips,
            tags=[],
        )
    except (TypeError, ValueError, HeadlessTransitionError) as exc:
        raise LiveBlindSkipParityCheckpointError(
            "live blind-skip checkpoint cannot restore exact headless authority"
        ) from exc


def _progression_signature(progression: BlindProgressionState) -> LiveBlindSkipProgression:
    if not progression.small_tag or not progression.big_tag:
        raise LiveBlindSkipParityCheckpointError(
            "headless blind-skip result lost retained Tag authority"
        )
    return LiveBlindSkipProgression(
        small_status=progression.small_status,
        big_status=progression.big_status,
        boss_status=progression.boss_status,
        blind_on_deck=progression.blind_on_deck,
        blind_ante=progression.blind_ante,
        small_tag=progression.small_tag,
        big_tag=progression.big_tag,
    )


def compare_live_blind_skip_replay(
    before: LiveBlindSkipParityCheckpoint,
    after: LiveBlindSkipParityCheckpoint,
    live_evidence: PublicStrategicTransitionEvidence,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> LiveBlindSkipReplayComparison:
    canonical_action = EnvAction.from_alias("SKIP_BLIND")
    if live_evidence.action != canonical_action:
        raise LiveBlindSkipParityCheckpointError(
            "blind-skip replay requires exact parameterless SKIP_BLIND evidence"
        )
    if after.public_snapshot.phase != "BLIND_SELECT" or after.active_tag_count != 0:
        raise LiveBlindSkipParityCheckpointError(
            "blind-skip replay requires a tag-free BLIND_SELECT post-checkpoint"
        )
    before_run = headless_blind_skip_run_from_live_checkpoint(before, translator=translator)
    translator = translator or DefaultBalatroStateTranslator()
    live_after = translator.translate(after.public_snapshot)
    checkpoint_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        canonical_action,
        live_after,
    )
    checkpoint_comparison = compare_public_strategic_evidence(
        live_evidence,
        checkpoint_evidence,
    )
    if not checkpoint_comparison.matches:
        joined = ", ".join(checkpoint_comparison.differences)
        raise LiveBlindSkipParityCheckpointError(
            f"live blind-skip evidence does not match checkpoint public state: {joined}"
        )
    try:
        result, simulator_evidence = skip_blind_with_public_evidence(before_run)
    except HeadlessTransitionError as exc:
        raise LiveBlindSkipParityCheckpointError(
            f"live checkpoint does not admit exact blind-skip replay: {exc}"
        ) from exc
    public_comparison = compare_public_strategic_evidence(live_evidence, simulator_evidence)
    differences = [f"public.{item}" for item in public_comparison.differences]
    if result.skips != after.skips:
        differences.append("private.skips.after")
    if _progression_signature(result.require_blind_progression_state()) != after.progression:
        differences.append("private.blind_progression.after")
    return LiveBlindSkipReplayComparison(
        matches=not differences,
        differences=tuple(differences),
        public=public_comparison,
        simulator_evidence=simulator_evidence,
    )
