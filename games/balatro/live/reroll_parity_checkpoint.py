"""Coherent parity-only checkpoint for exact ordinary paid shop rerolls.

The checkpoint keeps simulator replay authority separate from the policy-visible
``LiveBalatroSnapshot``. It is diagnostic R5 state, not an observation feature.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from games.balatro.env.actions import EnvAction
from games.balatro.env.parity import (
    PublicStrategicParityComparison,
    compare_public_strategic_evidence,
)
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
    reroll_shop_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import expected_base_reroll_cost_for_vouchers
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.rng_replay_capture import (
    LiveRNGReplayCaptureError,
    rng_replay_snapshot_from_live_memory,
)
from games.balatro.live.runtime.live_memory_shop_terms import (
    LiveShopRerollTerms,
    read_live_shop_reroll_terms,
)
from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError
from games.balatro.live.translator import DefaultBalatroStateTranslator


class LiveRerollParityCheckpointError(RuntimeError):
    """Raised when a coherent exact reroll replay checkpoint cannot be captured."""


@dataclass(frozen=True)
class LiveRerollParityCheckpoint:
    public_snapshot: LiveBalatroSnapshot
    rng_snapshot: dict[str, Any]
    reroll_terms: LiveShopRerollTerms
    active_tag_count: int


@dataclass(frozen=True)
class LiveRerollReplayComparison:
    """One exact reroll replay verdict across public and private authority.

    ``public`` remains the canonical R5 public comparison. Private replay state is
    represented only by named mismatch fields; RNG snapshots are never copied into
    policy-visible evidence or this comparison record.
    """

    matches: bool
    differences: tuple[str, ...]
    public: PublicStrategicParityComparison
    simulator_evidence: PublicStrategicTransitionEvidence


def _active_tag_count_from_live_memory(decoder, root) -> int:
    game_value = root.get("GAME")
    if game_value is None or getattr(game_value, "kind", None) != "table":
        raise LiveRerollParityCheckpointError("live Balatro G.GAME table is unavailable")
    try:
        game = decoder.string_fields(int(game_value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LiveRerollParityCheckpointError("unable to read live Balatro G.GAME table") from exc

    tags_value = game.get("tags")
    if tags_value is None or getattr(tags_value, "kind", None) != "table":
        raise LiveRerollParityCheckpointError("live Balatro G.GAME.tags table is unavailable")
    try:
        items = list(decoder.array_items(int(tags_value.value)))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LiveRerollParityCheckpointError("unable to read live Balatro active Tags") from exc
    for _, value in items:
        if value is None or getattr(value, "kind", None) != "table":
            raise LiveRerollParityCheckpointError("live Balatro active Tag array is malformed")
    return len(items)


def capture_live_reroll_parity_checkpoint(observer) -> LiveRerollParityCheckpoint:
    """Capture stable public + private replay authority before one paid reroll.

    Public observations are sampled before and after the private diagnostic reads.
    Any public change rejects the checkpoint instead of combining evidence from
    different game moments.
    """
    before = observer.observe()
    if not isinstance(before, LiveBalatroSnapshot):
        raise LiveRerollParityCheckpointError("observer did not return LiveBalatroSnapshot")
    if before.phase != "SHOP" or before.state_complete is not True:
        raise LiveRerollParityCheckpointError("reroll parity checkpoint requires complete SHOP")

    try:
        decoder, _, root = observer._root()
        rng_snapshot = rng_replay_snapshot_from_live_memory(decoder, root)
        active_tag_count = _active_tag_count_from_live_memory(decoder, root)
        reroll_terms = read_live_shop_reroll_terms(observer)
    except (LiveRNGReplayCaptureError, RuntimeError) as exc:
        if isinstance(exc, LiveRerollParityCheckpointError):
            raise
        raise LiveRerollParityCheckpointError("unable to capture exact live reroll replay authority") from exc

    after = observer.observe()
    if before != after:
        raise LiveRerollParityCheckpointError(
            "live public state changed while capturing reroll replay authority"
        )

    return LiveRerollParityCheckpoint(
        public_snapshot=deepcopy(before),
        rng_snapshot=deepcopy(rng_snapshot),
        reroll_terms=reroll_terms,
        active_tag_count=active_tag_count,
    )


def headless_reroll_run_from_live_checkpoint(
    checkpoint: LiveRerollParityCheckpoint,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> HeadlessRunState:
    """Restore the exact headless pre-reroll authority admitted by R2.

    This builder is intentionally narrow. Active Tags or free-reroll state are
    not normalized away; they remain unsupported by the ordinary paid-reroll
    owner and therefore reject the fixture.
    """
    if not isinstance(checkpoint, LiveRerollParityCheckpoint):
        raise TypeError("checkpoint must be LiveRerollParityCheckpoint")
    if checkpoint.active_tag_count != 0:
        raise LiveRerollParityCheckpointError(
            "ordinary paid-reroll parity does not admit active Tags"
        )
    if checkpoint.reroll_terms.free_rerolls != 0:
        raise LiveRerollParityCheckpointError(
            "ordinary paid-reroll parity does not admit free rerolls"
        )

    payload = checkpoint.public_snapshot.payload
    if payload.get("vouchers_observed") is not True or not isinstance(payload.get("vouchers"), list):
        raise LiveRerollParityCheckpointError(
            "live reroll checkpoint does not have exact Voucher reroll-cost state"
        )

    translator = translator or DefaultBalatroStateTranslator()
    public = translator.translate(checkpoint.public_snapshot)
    if public.phase != "SHOP" or not public.shop_active:
        raise LiveRerollParityCheckpointError("translated reroll checkpoint is not active SHOP")

    expected_base = expected_base_reroll_cost_for_vouchers(public)
    if expected_base is None:
        raise LiveRerollParityCheckpointError(
            "live reroll checkpoint does not have exact Voucher reroll-cost state"
        )
    try:
        restored_rng = BalatroRNG.from_snapshot(checkpoint.rng_snapshot)
        return HeadlessRunState(
            public=public,
            seed=restored_rng.seed,
            rng_state=checkpoint.rng_snapshot,
            base_reroll_cost=expected_base,
            reroll_cost=checkpoint.reroll_terms.cost,
            tags=[],
        )
    except (TypeError, ValueError, HeadlessTransitionError) as exc:
        raise LiveRerollParityCheckpointError(
            "live reroll checkpoint cannot restore exact headless authority"
        ) from exc


def compare_live_reroll_replay(
    before_checkpoint: LiveRerollParityCheckpoint,
    after_checkpoint: LiveRerollParityCheckpoint,
    live_evidence: PublicStrategicTransitionEvidence,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> LiveRerollReplayComparison:
    """Replay one captured paid reroll and compare public + private post-state.

    Durable strategic evidence proves the canonical production action boundary.
    The two coherent checkpoints supply the private RNG and reroll-cost authority
    that intentionally stays outside public R5 evidence. Mechanics are delegated
    to ``reroll_shop_with_public_evidence`` / ``reroll_base_main_shop``.
    """
    if not isinstance(live_evidence, PublicStrategicTransitionEvidence):
        raise TypeError("live_evidence must be PublicStrategicTransitionEvidence")

    canonical_action = EnvAction.from_alias("REROLL_SHOP")
    if live_evidence.action != canonical_action:
        raise LiveRerollParityCheckpointError(
            "reroll replay requires exact parameterless REROLL_SHOP live evidence"
        )

    before_run = headless_reroll_run_from_live_checkpoint(
        before_checkpoint,
        translator=translator,
    )
    after_run = headless_reroll_run_from_live_checkpoint(
        after_checkpoint,
        translator=translator,
    )

    checkpoint_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        canonical_action,
        after_run.public,
    )
    checkpoint_comparison = compare_public_strategic_evidence(
        live_evidence,
        checkpoint_evidence,
    )
    if not checkpoint_comparison.matches:
        joined = ", ".join(checkpoint_comparison.differences)
        raise LiveRerollParityCheckpointError(
            f"live reroll evidence does not match checkpoint public state: {joined}"
        )

    try:
        reroll, simulator_evidence = reroll_shop_with_public_evidence(before_run)
    except HeadlessTransitionError as exc:
        raise LiveRerollParityCheckpointError(
            "live reroll checkpoint does not admit exact headless reroll replay"
        ) from exc

    public_comparison = compare_public_strategic_evidence(
        live_evidence,
        simulator_evidence,
    )
    differences = [
        f"public.{difference}" for difference in public_comparison.differences
    ]
    if reroll.previous_cost != before_checkpoint.reroll_terms.cost:
        differences.append("reroll.previous_cost")
    if reroll.next_cost != after_checkpoint.reroll_terms.cost:
        differences.append("reroll.next_cost")
    if reroll.run.rng_snapshot() != after_checkpoint.rng_snapshot:
        differences.append("rng.after")

    return LiveRerollReplayComparison(
        matches=not differences,
        differences=tuple(differences),
        public=public_comparison,
        simulator_evidence=simulator_evidence,
    )
