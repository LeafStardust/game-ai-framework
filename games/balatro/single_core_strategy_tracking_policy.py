from __future__ import annotations

"""Keep known strategy missing-piece tracking alive from the first defining core.

The canonical motif layer historically required at least two present components
before a motif existed at all.  That is safe for avoiding infrastructure-only false
positives, but it leaves a real strategic blind spot: owning a defining Joker such
as Burnt Joker, Vampire, or Midas Mask can still produce no FORMING strategy when
its supporting infrastructure is absent.  The agent then cannot explicitly seek the
rest of a package until it happens to acquire another component by accident.

This policy promotes only motifs containing a defining core component. Ambient deck
infrastructure by itself remains ABSENT.  A one-core motif is exposed as FORMING,
never PINNED, so StrategyPlan can enumerate missing pieces and D2 can recruit them
without granting retention/execution authority prematurely.
"""

from dataclasses import replace

import games.balatro.bonds.composer as composer_module
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
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
    required = _DEFINING_CORES.get(str(motif.motif_id), frozenset())
    if not required:
        return False
    present = {_token(value) for value in tuple(motif.present_components or ())}
    return bool(required.intersection(present))


def _promote_single_core_motifs(motifs) -> tuple[MotifEvaluation, ...]:
    result: list[MotifEvaluation] = []
    for motif in tuple(motifs or ()):
        if (
            motif.state == MotifState.ABSENT
            and motif.present_components
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

    original_evaluate_motifs = composer_module.evaluate_motifs
    original_form_strategy_candidates = composer_module.form_strategy_candidates

    def evaluate_motifs(state, developments):
        return _promote_single_core_motifs(
            original_evaluate_motifs(state, developments)
        )

    def form_strategy_candidates(developments, motifs=()):
        motif_tuple = tuple(motifs or ())
        base = original_form_strategy_candidates(developments, motif_tuple)
        return _augment_single_core_candidates(base, motif_tuple)

    composer_module.evaluate_motifs = evaluate_motifs
    composer_module.form_strategy_candidates = form_strategy_candidates
    composer_module._single_core_strategy_tracking_installed = True
