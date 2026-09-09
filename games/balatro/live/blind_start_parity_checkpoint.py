"""Coherent private R5 checkpoint for exact ordinary blind-start replay."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from games.balatro.env.actions import EnvAction
from games.balatro.env.parity import PublicStrategicParityComparison, compare_public_strategic_evidence
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
    select_blind_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.live.private_run_state import (
    LivePrivateRunStateError,
    active_tag_count_from_live_memory,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.rng_replay_capture import (
    LiveRNGReplayCaptureError,
    rng_replay_snapshot_from_live_memory,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator


class LiveBlindStartParityCheckpointError(RuntimeError):
    """Raised when exact blind-start replay authority is unavailable."""


@dataclass(frozen=True)
class LiveBlindStartParityCheckpoint:
    public_snapshot: LiveBalatroSnapshot
    rng_snapshot: dict[str, Any]
    active_tag_count: int


@dataclass(frozen=True)
class LiveBlindStartReplayComparison:
    matches: bool
    differences: tuple[str, ...]
    public: PublicStrategicParityComparison
    simulator_evidence: PublicStrategicTransitionEvidence


def capture_live_blind_start_parity_checkpoint(
    observer,
    *,
    expected_phase: str,
) -> LiveBlindStartParityCheckpoint:
    if expected_phase not in {"BLIND_SELECT", "SELECTING_HAND"}:
        raise ValueError("blind-start checkpoint phase must be BLIND_SELECT or SELECTING_HAND")
    before = observer.observe()
    if not isinstance(before, LiveBalatroSnapshot):
        raise LiveBlindStartParityCheckpointError(
            "observer did not return LiveBalatroSnapshot"
        )
    if before.phase != expected_phase or before.state_complete is not True:
        raise LiveBlindStartParityCheckpointError(
            f"blind-start parity checkpoint requires complete {expected_phase}"
        )
    try:
        decoder, _, root = observer._root()
        rng_snapshot = rng_replay_snapshot_from_live_memory(decoder, root)
        active_tag_count = active_tag_count_from_live_memory(decoder, root)
    except (LiveRNGReplayCaptureError, LivePrivateRunStateError, OSError, RuntimeError) as exc:
        raise LiveBlindStartParityCheckpointError(
            "unable to capture exact live blind-start replay authority"
        ) from exc
    after = observer.observe()
    if before != after:
        raise LiveBlindStartParityCheckpointError(
            "live public state changed while capturing blind-start replay authority"
        )
    return LiveBlindStartParityCheckpoint(
        public_snapshot=deepcopy(before),
        rng_snapshot=deepcopy(rng_snapshot),
        active_tag_count=active_tag_count,
    )


def _restore_complete_deck_identity(public) -> None:
    owned = public.owned_deck
    if not isinstance(owned, list) or not owned:
        raise LiveBlindStartParityCheckpointError(
            "blind-start checkpoint requires authoritative permanent owned deck"
        )
    owned_by_id = {card.live_id: card for card in owned if type(card.live_id) is int}
    if len(owned_by_id) != len(owned):
        raise LiveBlindStartParityCheckpointError(
            "blind-start checkpoint requires unique exact permanent card IDs"
        )
    if len(public.deck) != len(owned):
        raise LiveBlindStartParityCheckpointError(
            "blind-start checkpoint deck is not the complete permanent deck"
        )
    rebound = []
    for card in public.deck:
        if type(card.live_id) is not int or card.live_id not in owned_by_id:
            raise LiveBlindStartParityCheckpointError(
                "blind-start checkpoint deck IDs do not match permanent owned deck"
            )
        canonical = owned_by_id[card.live_id]
        if card != canonical:
            raise LiveBlindStartParityCheckpointError(
                "blind-start checkpoint deck card state differs from permanent owned deck"
            )
        rebound.append(canonical)
    if len({id(card) for card in rebound}) != len(owned):
        raise LiveBlindStartParityCheckpointError(
            "blind-start checkpoint deck IDs are not unique"
        )
    public.deck = rebound


def headless_blind_start_run_from_live_checkpoint(
    checkpoint: LiveBlindStartParityCheckpoint,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> HeadlessRunState:
    if not isinstance(checkpoint, LiveBlindStartParityCheckpoint):
        raise TypeError("checkpoint must be LiveBlindStartParityCheckpoint")
    if checkpoint.public_snapshot.phase != "BLIND_SELECT":
        raise LiveBlindStartParityCheckpointError(
            "headless blind-start restoration requires BLIND_SELECT checkpoint"
        )
    if checkpoint.active_tag_count != 0:
        raise LiveBlindStartParityCheckpointError(
            "ordinary blind-start parity does not admit active Tags"
        )
    translator = translator or DefaultBalatroStateTranslator()
    public = translator.translate(checkpoint.public_snapshot)
    if public.phase != "BLIND_SELECT":
        raise LiveBlindStartParityCheckpointError(
            "translated blind-start checkpoint is not BLIND_SELECT"
        )
    _restore_complete_deck_identity(public)
    try:
        rng = BalatroRNG.from_snapshot(checkpoint.rng_snapshot)
        return HeadlessRunState(
            public=public,
            seed=rng.seed,
            rng_state=checkpoint.rng_snapshot,
            tags=[],
        )
    except (TypeError, ValueError, HeadlessTransitionError) as exc:
        raise LiveBlindStartParityCheckpointError(
            "live blind-start checkpoint cannot restore exact headless authority"
        ) from exc


def compare_live_blind_start_replay(
    before: LiveBlindStartParityCheckpoint,
    after: LiveBlindStartParityCheckpoint,
    live_evidence: PublicStrategicTransitionEvidence,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> LiveBlindStartReplayComparison:
    if not isinstance(live_evidence, PublicStrategicTransitionEvidence):
        raise TypeError("live_evidence must be PublicStrategicTransitionEvidence")
    canonical_action = EnvAction.from_alias("SELECT_BLIND")
    if live_evidence.action != canonical_action:
        raise LiveBlindStartParityCheckpointError(
            "blind-start replay requires exact parameterless SELECT_BLIND evidence"
        )
    if after.public_snapshot.phase != "SELECTING_HAND" or after.active_tag_count != 0:
        raise LiveBlindStartParityCheckpointError(
            "blind-start replay requires a tag-free SELECTING_HAND post-checkpoint"
        )
    before_run = headless_blind_start_run_from_live_checkpoint(
        before,
        translator=translator,
    )
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
        raise LiveBlindStartParityCheckpointError(
            f"live blind-start evidence does not match checkpoint public state: {joined}"
        )
    try:
        result, simulator_evidence = select_blind_with_public_evidence(before_run)
    except HeadlessTransitionError as exc:
        raise LiveBlindStartParityCheckpointError(
            f"live checkpoint does not admit exact blind-start replay: {exc}"
        ) from exc
    public_comparison = compare_public_strategic_evidence(
        live_evidence,
        simulator_evidence,
    )
    differences = [
        f"public.{difference}" for difference in public_comparison.differences
    ]
    if result.rng_snapshot() != after.rng_snapshot:
        differences.append("rng.after")
    return LiveBlindStartReplayComparison(
        matches=not differences,
        differences=tuple(differences),
        public=public_comparison,
        simulator_evidence=simulator_evidence,
    )
