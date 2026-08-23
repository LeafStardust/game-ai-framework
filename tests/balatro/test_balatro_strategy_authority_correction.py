from __future__ import annotations

from types import SimpleNamespace

import games.balatro  # install package-level authorities
import games.balatro.strategy_plan_pack_policy as pack_goal_module
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_semantics import (
    StrategyCandidate,
    StrategyCommitment,
)
from games.balatro.strategy_authority_correction_policy import (
    _component_match,
    _correct_candidate,
    _forming_plan,
)


def _candidate(
    *,
    strategy_id: str,
    commitment: StrategyCommitment = StrategyCommitment.PINNED,
    motif_ids=(),
    sources=(),
    bonds=("kings", "held_cards"),
    prescriptions=(),
):
    return StrategyCandidate(
        strategy_id=strategy_id,
        bond_ids=tuple(bonds),
        sources=tuple(sources),
        roles=(),
        links=(),
        motif_ids=tuple(motif_ids),
        commitment=commitment,
        confidence=0.8,
        strength=12.0,
        prescriptions=tuple(prescriptions),
    )


def _baron_motif(*, present, missing):
    return MotifEvaluation(
        motif_id="baron_mime_steel",
        state=MotifState.POTENTIAL,
        relevant_bonds=("held_cards", "held_retrigger", "steel", "kings"),
        present_components=tuple(present),
        missing_components=tuple(missing),
        prescriptions=("preserve_held_kings_and_steel",),
    )


def _dev(bond_id: str, rank=BondRank.R1):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=5.0,
        rank=rank,
        next_rank_threshold=9.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def test_baron_without_mime_stays_forming_even_at_half_motif_completion():
    motif = _baron_motif(
        present=("BARON", "KING_INFRASTRUCTURE"),
        missing=("MIME", "STEEL_INFRASTRUCTURE"),
    )
    candidate = _candidate(
        strategy_id="baron_mime_steel",
        motif_ids=("baron_mime_steel",),
        sources=("BARON", "KING_INFRASTRUCTURE"),
        bonds=("held_cards", "held_retrigger", "steel", "kings"),
    )

    corrected = _correct_candidate(candidate, (motif,))

    assert corrected.commitment == StrategyCommitment.FORMING
    assert not corrected.pinned


def test_baron_and_mime_can_pin_while_infrastructure_is_still_being_built():
    motif = _baron_motif(
        present=("BARON", "MIME"),
        missing=("KING_INFRASTRUCTURE", "STEEL_INFRASTRUCTURE"),
    )
    candidate = _candidate(
        strategy_id="baron_mime_steel",
        motif_ids=("baron_mime_steel",),
        sources=("BARON", "MIME"),
        bonds=("held_cards", "held_retrigger", "steel", "kings"),
    )

    corrected = _correct_candidate(candidate, (motif,))

    assert corrected.commitment == StrategyCommitment.PINNED


def test_one_concrete_joker_plus_ambient_features_cannot_pin_generic_strategy():
    candidate = _candidate(
        strategy_id="behavior:aces+straight+tarot",
        sources=("Superposition", "feature:rank:A", "feature:hand:STRAIGHT"),
        bonds=("aces", "straight", "tarot"),
    )

    corrected = _correct_candidate(candidate, ())

    assert corrected.commitment == StrategyCommitment.FORMING


def test_two_concrete_jokers_can_retain_generic_pinned_authority():
    candidate = _candidate(
        strategy_id="behavior:face_cards+played_retrigger",
        sources=("Photograph", "Hanging Chad", "feature:rank:K"),
        bonds=("face_cards", "played_retrigger"),
    )

    corrected = _correct_candidate(candidate, ())

    assert corrected.commitment == StrategyCommitment.PINNED


def test_forming_known_plan_tracks_missing_core_without_execution_prescriptions():
    motif = _baron_motif(
        present=("BARON", "KING_INFRASTRUCTURE"),
        missing=("MIME", "STEEL_INFRASTRUCTURE"),
    )
    candidate = _candidate(
        strategy_id="baron_mime_steel",
        commitment=StrategyCommitment.FORMING,
        motif_ids=("baron_mime_steel",),
        sources=("BARON", "KING_INFRASTRUCTURE"),
        bonds=("held_cards", "held_retrigger", "steel", "kings"),
        prescriptions=("preserve_held_kings_and_steel",),
    )
    developments = tuple(
        _dev(bond_id)
        for bond_id in ("held_cards", "held_retrigger", "steel", "kings")
    )

    plan = _forming_plan(candidate, developments, (motif,))

    assert plan is not None
    assert plan.commitment == StrategyCommitment.FORMING
    assert "seek_component:MIME" in plan.prescriptions
    assert "seek_component:STEEL_INFRASTRUCTURE" in plan.prescriptions
    assert "preserve_held_kings_and_steel" not in plan.prescriptions
    assert pack_goal_module._goal_ids(plan) == ()


def test_missing_core_component_match_is_exact_and_does_not_match_infrastructure():
    motif = _baron_motif(
        present=("BARON", "KING_INFRASTRUCTURE"),
        missing=("MIME", "STEEL_INFRASTRUCTURE"),
    )
    candidate = _candidate(
        strategy_id="baron_mime_steel",
        commitment=StrategyCommitment.FORMING,
        motif_ids=("baron_mime_steel",),
        sources=("BARON", "KING_INFRASTRUCTURE"),
        bonds=("held_cards", "held_retrigger", "steel", "kings"),
    )
    developments = tuple(
        _dev(bond_id)
        for bond_id in ("held_cards", "held_retrigger", "steel", "kings")
    )
    plan = _forming_plan(candidate, developments, (motif,))

    assert _component_match(plan, SimpleNamespace(name="Mime")) == "MIME"
    assert _component_match(plan, SimpleNamespace(name="Steel Joker")) is None
