from types import SimpleNamespace

import games.balatro.build_component_roles as roles_module
from games.balatro.bonds.composer import Composition
from games.balatro.bonds.model import (
    BondContribution,
    BondDevelopment,
    BondRank,
    BondRealization,
)
from games.balatro.build_component_roles import (
    BuildComponentRole,
    BuildComponentRoleClassifier,
)
from games.balatro.build_health import EngineState, RealizedEngineStrength


def _joker(name):
    return SimpleNamespace(name=name)


def _development(bond_id, source, rank, realization):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=float(max(1, int(rank))) * 5.0,
        rank=rank,
        next_rank_threshold=None,
        contributions=(BondContribution(source, 5.0),),
        realization=realization,
    )


class _Engines:
    def analyze(self, state):
        del state
        return (
            RealizedEngineStrength(
                engine_id="hologram",
                state=EngineState.OWNED_INACTIVE,
                current_strength=1.0,
            ),
        )


def test_component_roles_use_selected_bonds_realized_engines_and_conflicts(monkeypatch):
    developments = (
        _development("flush", "The Tribe", BondRank.R4, BondRealization.ACTIVE),
        _development("flush", "Droll Joker", BondRank.R2, BondRealization.PARTIAL),
        _development("deck_growth", "Hologram", BondRank.R2, BondRealization.PARTIAL),
        _development("pair", "Conflict", BondRank.R3, BondRealization.ACTIVE),
    )
    composition = Composition(
        bond_ids=("flush", "deck_growth"),
        motifs=(),
        conflicts=(("pair", "flush"),),
        synergies=(),
        coherence_score=8.0,
        motif_distance=(),
    )
    monkeypatch.setattr(
        roles_module,
        "evaluate_bond_structure",
        lambda state: (developments, composition),
    )
    state = SimpleNamespace(
        jokers=[
            _joker("The Tribe"),
            _joker("Droll Joker"),
            _joker("Hologram"),
            _joker("Misprint"),
            _joker("Conflict"),
        ]
    )
    classifier = BuildComponentRoleClassifier(engine_analyzer=_Engines())

    assessments = {item.name: item for item in classifier.classify(state)}

    assert assessments["The Tribe"].role == BuildComponentRole.CORE
    assert assessments["The Tribe"].bond_id == "flush"
    assert assessments["The Tribe"].bond_rank == BondRank.R4
    assert assessments["Droll Joker"].role == BuildComponentRole.SUPPORT
    assert assessments["Hologram"].role == BuildComponentRole.ENGINE
    assert assessments["Hologram"].realized_engine_id == "hologram"
    assert assessments["Misprint"].role == BuildComponentRole.FILLER
    assert assessments["Conflict"].role == BuildComponentRole.CONFLICT
    assert assessments["Conflict"].bond_id == "pair"
