from __future__ import annotations

"""Keep known strategy missing-piece tracking alive from the first defining core.

The canonical motif layer historically requires at least two present components
before a motif survives composer filtering. That is safe for avoiding
infrastructure-only false positives, but it leaves a blind spot: owning a defining
Joker such as Burnt Joker or Vampire can produce no FORMING strategy while its
supporting infrastructure is absent.

This policy promotes only motifs containing a defining core component. Ambient deck
infrastructure by itself remains ABSENT. A one-core motif is exposed as FORMING,
never PINNED, so StrategyPlan can enumerate missing pieces without granting strategy
execution/retention authority prematurely.
"""

from dataclasses import replace

import games.balatro.bonds.composer as composer_module
from games.balatro.bonds.motifs import MotifEvaluation, MotifState, evaluate_motifs as raw_evaluate_motifs
from games.balatro.bonds.strategy_semantics import (
    StrategyCandidate,
    StrategyCommitment,
)


_DEFINING_CORES: dict[str, frozenset[str]] = {
    "baron_mime_steel": frozenset({"BARON", "MIME"}),
    "photograph_hanging_chad": frozenset({"PHOTOGRAPH", "HANGING_CHAD"}),
    "vampire_midas": frozenset({"VAMPIRE", "MIDAS_MASK"}),
    "burnt_target_level": frozenset({"BURNT_JOKER"}),
    "low_rank_hack_retrigger": frozenset({"HACK"}),
}


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _has_defining_core(motif: MotifEvaluation) -> bool:
    defining = _DEFINING_CORES.get(str(motif.motif_id), frozenset())
    if not defining:
        return False
    present = {_token(value) for value in tuple(motif.present_components or ())}
    return bool(defining.intersection(present))


def _promote_single_core_motifs(motifs) -> tuple[MotifEvaluation, ...]:
    result: list[MotifEvaluation] = []
    for motif in tuple(motifs or ()):
        if (
            motif.state == MotifState.ABSENT
            and len(tuple(motif.present_components or ())) == 1
            and _has_defining_core(motif)
        ):
            motif = replace(motif, state=MotifState.POTENTIAL)
        result.append(motif)
    return tuple(result)


def _single_core_candidate(motif: MotifEvaluation) -> StrategyCandidate:
    present = tuple(dict.fromkeys(str(value) for value in motif.present_components))
    total = len(present) + len(tuple(motif.missing_components or ()))
    completion = 0.0 if total <= 0 else len(present) / total
    confidence = min(0.57, 0.25 + 0.45 * completion)
    return StrategyCandidate(
        strategy_id=str(motif.motif_id),
        bond_ids=tuple(sorted(set(motif.relevant_bonds))),
        sources=present,
        roles=(),
        links=(),
        motif_ids=(str(motif.motif_id),),
        commitment=StrategyCommitment.FORMING,
        confidence=confidence,
        strength=2.0 + 4.0 * confidence + len(present),
        prescriptions=tuple(motif.prescriptions or ()),
    )


def _augment_single_core_candidates(candidates, motifs) -> tuple[StrategyCandidate, ...]:
    candidates = tuple(candidates or ())
    covered = {
        str(motif_id)
        for candidate in candidates
        for motif_id in tuple(candidate.motif_ids or ())
    }
    additions = [
        _single_core_candidate(motif)
        for motif in tuple(motifs or ())
        if motif.state == MotifState.POTENTIAL
        and str(motif.motif_id) not in covered
        and len(tuple(motif.present_components or ())) == 1
        and _has_defining_core(motif)
    ]
    if not additions:
        return candidates
    return tuple(
        sorted(
            (*candidates, *additions),
            key=lambda candidate: (
                int(candidate.commitment),
                candidate.confidence,
                candidate.strength,
                bool(candidate.motif_ids),
                candidate.strategy_id,
            ),
            reverse=True,
        )
    )


def install_single_core_strategy_tracking_policy() -> None:
    if getattr(composer_module, "_single_core_strategy_tracking_installed", False):
        return

    original_compose = composer_module.compose_build

    def compose_build(state, developments):
        developments = tuple(developments)
        base = original_compose(state, developments)

        # Re-evaluate from the canonical motif evaluators because original_compose
        # has already discarded ABSENT motifs. Only defining-core singletons are
        # promoted; ordinary ambient infrastructure never enters this path.
        raw_motifs = raw_evaluate_motifs(state, developments)
        promoted = _promote_single_core_motifs(raw_motifs)
        single_core = tuple(
            motif
            for motif in promoted
            if motif.state == MotifState.POTENTIAL
            and len(tuple(motif.present_components or ())) == 1
            and _has_defining_core(motif)
        )
        if not single_core:
            return base

        motif_by_id = {str(motif.motif_id): motif for motif in tuple(base.motifs or ())}
        for motif in single_core:
            motif_by_id.setdefault(str(motif.motif_id), motif)
        motifs = tuple(motif_by_id.values())
        candidates = _augment_single_core_candidates(base.strategy_candidates, motifs)

        # Do not create a StrategyPlan here. The strategy-authority correction layer
        # installed immediately after this policy converts the FORMING candidate into
        # a bounded missing-piece scouting plan while preserving pinned_strategy_id=None.
        return replace(
            base,
            motifs=motifs,
            motif_distance=tuple(
                (motif.motif_id, motif.missing_count)
                for motif in motifs
            ),
            strategy_candidates=candidates,
        )

    composer_module.compose_build = compose_build
    composer_module._single_core_strategy_tracking_installed = True
