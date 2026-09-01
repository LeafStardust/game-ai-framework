from __future__ import annotations

from types import SimpleNamespace

from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization, MechanicalRole
from games.balatro.bonds.strategy_semantics import StrategyCommitment, form_strategy_candidates
from games.balatro.state import BalatroState


def _dev(bond_id, contribution, *, rank=BondRank.R0):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=float(contribution.value),
        rank=rank,
        next_rank_threshold=None,
        contributions=(contribution,),
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


def _joker(name: str):
    return SimpleNamespace(name=name)


def test_r0_mechanical_evidence_can_form_and_pin_a_strategy_before_rank_authority():
    baron = _dev(
        "kings",
        BondContribution(
            "Baron",
            3.0,
            roles=(MechanicalRole.HELD_RANK_PAYOFF,),
            targets=("KINGS",),
        ),
    )
    mime = _dev(
        "held_retrigger",
        BondContribution(
            "Mime",
            3.0,
            roles=(MechanicalRole.HELD_RETRIGGER,),
            targets=("HELD_CARD_EFFECTS",),
        ),
    )

    candidates = form_strategy_candidates((baron, mime))

    assert candidates
    candidate = candidates[0]
    assert candidate.commitment >= StrategyCommitment.PINNED
    assert set(candidate.bond_ids) == {"held_retrigger", "kings"}
    assert any(link.relation == "RETRIGGER_AMPLIFIES_HELD_PAYOFF" for link in candidate.links)


def test_unrelated_r0_evidence_remains_exploratory_and_does_not_get_strategy_authority():
    left = _dev(
        "cash",
        BondContribution("cash thing", 8.0, roles=(MechanicalRole.ECONOMY_ENGINE,), targets=("CASH",)),
    )
    right = _dev(
        "steel",
        BondContribution("steel thing", 8.0, roles=(MechanicalRole.HELD_CARD_XMULT,), targets=("STEEL_CARDS",)),
    )

    candidates = form_strategy_candidates((left, right))

    assert candidates
    assert all(candidate.commitment == StrategyCommitment.EXPLORATORY for candidate in candidates)
    assert all(not candidate.pinned for candidate in candidates)
    assert all(not candidate.links for candidate in candidates)


def test_baron_mime_is_pinned_as_known_engine_before_steel_is_present():
    state = BalatroState()
    state.jokers = [_joker("Baron"), _joker("Mime")]

    developments, composition = evaluate_bond_composition(state)

    assert composition.pinned_strategy_id == "baron_mime_steel"
    candidate = next(c for c in composition.strategy_candidates if c.strategy_id == "baron_mime_steel")
    assert candidate.commitment >= StrategyCommitment.PINNED
    assert "BARON" in next(m.present_components for m in composition.motifs if m.motif_id == "baron_mime_steel")
    assert "MIME" in next(m.present_components for m in composition.motifs if m.motif_id == "baron_mime_steel")
    assert "STEEL_INFRASTRUCTURE" in next(m.missing_components for m in composition.motifs if m.motif_id == "baron_mime_steel")
    assert "prefer_kings_and_steel_creation" in composition.prescriptions


def test_strategy_diagnostics_explain_why_baron_mime_is_pinned():
    state = BalatroState()
    state.jokers = [_joker("Baron"), _joker("Mime")]

    payload = bond_strategy_diagnostics(state)

    assert payload["pinned_strategy"] == "baron_mime_steel"
    strategy = next(item for item in payload["strategy_candidates"] if item["strategy_id"] == "baron_mime_steel")
    assert strategy["pinned"] is True
    assert strategy["commitment"] in {"PINNED", "ESTABLISHED", "DOMINANT"}
    assert any(link["relation"] == "RETRIGGER_AMPLIFIES_HELD_PAYOFF" for link in strategy["links"])
    assert "prefer_kings_and_steel_creation" in strategy["prescriptions"]
