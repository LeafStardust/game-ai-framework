from __future__ import annotations

from types import SimpleNamespace

import games.balatro.bonds.behavior_strategy as behavior
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.build.effects import EffectDescriptor


def _dev(bond_id: str, source: str):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=2.0,
        rank=BondRank.R0,
        next_rank_threshold=4.0,
        contributions=(BondContribution(source, 2.0),),
        realization=BondRealization.DORMANT,
    )


class _Profile:
    def __init__(self):
        self.effects = (
            EffectDescriptor(
                source="ProducerJoker",
                kind="JOKER",
                produces=frozenset({"engine:foo"}),
            ),
            EffectDescriptor(
                source="ConsumerJoker",
                kind="JOKER",
                requires=frozenset({"engine:foo"}),
                scales_with=frozenset({"engine:bar"}),
            ),
        )
        self.feature_strengths = ()

    def descriptors(self, *, kind=None):
        if kind is None:
            return self.effects
        return tuple(item for item in self.effects if item.kind == kind)


class _Profiler:
    def profile(self, state):
        return _Profile()


class _SuitProfile:
    def __init__(self, clubs):
        self.effects = (
            EffectDescriptor(
                source="GluttonousJoker",
                kind="JOKER",
                requires=frozenset({"suit:Clubs"}),
                produces=frozenset({"score:mult"}),
            ),
        )
        self.deck_size = 52
        self.feature_strengths = (("suit:Clubs", float(clubs)),)

    def descriptors(self, *, kind=None):
        if kind is None:
            return self.effects
        return tuple(item for item in self.effects if item.kind == kind)


def test_behavior_descriptors_form_strategy_without_pairwise_bond_relationship(monkeypatch):
    monkeypatch.setattr(behavior, "BalatroBuildProfiler", _Profiler)
    devs = (_dev("alpha", "Producer"), _dev("beta", "Consumer"))

    candidates = behavior.form_behavior_strategy_candidates(SimpleNamespace(), devs)

    assert candidates
    candidate = candidates[0]
    assert candidate.commitment >= StrategyCommitment.PINNED
    assert set(candidate.bond_ids) == {"alpha", "beta"}
    assert any(link.relation == "OUTPUT_SATISFIES_REQUIREMENT" for link in candidate.links)


def test_behavior_strategy_exposes_unmet_feature_goal(monkeypatch):
    monkeypatch.setattr(behavior, "BalatroBuildProfiler", _Profiler)
    devs = (_dev("alpha", "Producer"), _dev("beta", "Consumer"))

    candidate = behavior.form_behavior_strategy_candidates(SimpleNamespace(), devs)[0]

    assert "seek_feature:engine:bar" in candidate.prescriptions
    assert "seek_feature:engine:foo" not in candidate.prescriptions


def test_merge_keeps_role_and_behavior_evidence_for_same_strategy():
    from games.balatro.bonds.strategy_semantics import SemanticLink, StrategyCandidate

    role = StrategyCandidate(
        strategy_id="engine",
        bond_ids=("a",),
        sources=("role-source",),
        roles=(),
        links=(),
        motif_ids=("engine",),
        commitment=StrategyCommitment.PINNED,
        confidence=0.6,
        strength=5.0,
        prescriptions=("known-prescription",),
    )
    discovered = StrategyCandidate(
        strategy_id="engine",
        bond_ids=("b",),
        sources=("behavior-source",),
        roles=(),
        links=(SemanticLink("a", "x", "b", "y", "OUTPUT_SATISFIES_REQUIREMENT"),),
        motif_ids=("engine",),
        commitment=StrategyCommitment.ESTABLISHED,
        confidence=0.8,
        strength=7.0,
        prescriptions=("seek_feature:test",),
    )

    merged = behavior.merge_strategy_candidates((role,), (discovered,))[0]

    assert merged.commitment == StrategyCommitment.ESTABLISHED
    assert set(merged.bond_ids) == {"a", "b"}
    assert set(merged.sources) == {"role-source", "behavior-source"}
    assert set(merged.prescriptions) == {"known-prescription", "seek_feature:test"}
    assert merged.links


def test_stock_suit_density_does_not_form_phantom_behavior_strategy(monkeypatch):
    monkeypatch.setattr(
        behavior,
        "BalatroBuildProfiler",
        lambda: SimpleNamespace(profile=lambda state: _SuitProfile(13)),
    )

    candidates = behavior.form_behavior_strategy_candidates(
        SimpleNamespace(),
        (_dev("clubs", "Gluttonous Joker"),),
    )

    assert candidates == ()


def test_excess_suit_density_can_form_real_behavior_strategy(monkeypatch):
    monkeypatch.setattr(
        behavior,
        "BalatroBuildProfiler",
        lambda: SimpleNamespace(profile=lambda state: _SuitProfile(18)),
    )

    candidates = behavior.form_behavior_strategy_candidates(
        SimpleNamespace(),
        (_dev("clubs", "Gluttonous Joker"),),
    )

    assert candidates
