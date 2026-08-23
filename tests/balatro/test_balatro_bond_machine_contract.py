from __future__ import annotations

from types import SimpleNamespace

import pytest

import games.balatro.bonds.behavior_strategy as behavior
from games.balatro.bonds.model import (
    BondContribution,
    BondDevelopment,
    BondRank,
    BondRealization,
    MechanicalRole,
)
from games.balatro.bonds.strategy_semantics import StrategyCommitment, form_strategy_candidates, pinned_strategy
from games.balatro.build.effects import EffectDescriptor


def _dev(bond_id: str, source: str, *roles: MechanicalRole, target: str = "ENGINE") -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=3.0,
        rank=BondRank.R0,
        next_rank_threshold=4.0,
        contributions=(
            BondContribution(source, 3.0, roles=tuple(roles), targets=(target,)),
        ),
        target=target,
        realization=BondRealization.PARTIAL,
    )


@pytest.mark.parametrize(
    ("left_role", "right_role", "expected_relation"),
    (
        (MechanicalRole.HELD_RETRIGGER, MechanicalRole.HELD_RANK_PAYOFF, "RETRIGGER_AMPLIFIES_HELD_PAYOFF"),
        (MechanicalRole.HELD_RETRIGGER, MechanicalRole.HELD_STATE_PAYOFF, "RETRIGGER_AMPLIFIES_HELD_PAYOFF"),
        (MechanicalRole.HELD_RETRIGGER, MechanicalRole.HELD_CARD_XMULT, "RETRIGGER_AMPLIFIES_HELD_XMULT"),
        (MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.RANK_PAYOFF, "DENSITY_SUPPORTS_RANK_PAYOFF"),
        (MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.SUIT_PAYOFF, "DENSITY_SUPPORTS_SUIT_PAYOFF"),
        (MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.ENHANCEMENT_PAYOFF, "DENSITY_SUPPORTS_ENHANCEMENT_PAYOFF"),
        (MechanicalRole.ENHANCEMENT_FEED, MechanicalRole.ENHANCEMENT_PAYOFF, "FEED_SUPPORTS_ENHANCEMENT_PAYOFF"),
        (MechanicalRole.DECK_THIN_ENGINE, MechanicalRole.DECK_THIN_PAYOFF, "ENGINE_FEEDS_DECK_THIN_PAYOFF"),
        (MechanicalRole.ECONOMY_ENGINE, MechanicalRole.ECONOMY_PAYOFF, "ENGINE_FEEDS_ECONOMY_PAYOFF"),
        (MechanicalRole.HAND_LEVEL_ENGINE, MechanicalRole.HAND_PAYOFF, "LEVEL_ENGINE_SUPPORTS_HAND_PAYOFF"),
        (MechanicalRole.COPY_ENGINE, MechanicalRole.SCALER, "COPY_AMPLIFIES_SCALER"),
        (MechanicalRole.COPY_ENGINE, MechanicalRole.HELD_RETRIGGER, "COPY_AMPLIFIES_RETRIGGER"),
        (MechanicalRole.COPY_ENGINE, MechanicalRole.HELD_RANK_PAYOFF, "COPY_AMPLIFIES_HELD_PAYOFF"),
        (MechanicalRole.COPY_ENGINE, MechanicalRole.HAND_PAYOFF, "COPY_AMPLIFIES_HAND_PAYOFF"),
        (MechanicalRole.COPY_ENGINE, MechanicalRole.ENHANCEMENT_PAYOFF, "COPY_AMPLIFIES_ENHANCEMENT_PAYOFF"),
    ),
)
def test_role_semantics_form_pinnable_strategy_for_every_supported_interaction_family(
    left_role: MechanicalRole,
    right_role: MechanicalRole,
    expected_relation: str,
) -> None:
    candidates = form_strategy_candidates(
        (
            _dev("left", "Left", left_role),
            _dev("right", "Right", right_role),
        )
    )

    candidate = pinned_strategy(candidates)
    assert candidate is not None
    assert candidate.commitment >= StrategyCommitment.PINNED
    assert any(link.relation == expected_relation for link in candidate.links)


class _Profile:
    def __init__(self, left: EffectDescriptor, right: EffectDescriptor):
        self.effects = (left, right)
        self.feature_strengths = ()

    def descriptors(self, *, kind=None):
        if kind is None:
            return self.effects
        return tuple(effect for effect in self.effects if effect.kind == kind)


class _Profiler:
    profile_value = None

    def profile(self, state):
        return self.profile_value


@pytest.mark.parametrize(
    ("left", "right", "expected_relation"),
    (
        (
            EffectDescriptor(source="ProducerJoker", kind="JOKER", produces=frozenset({"engine:x"})),
            EffectDescriptor(source="ConsumerJoker", kind="JOKER", requires=frozenset({"engine:x"})),
            "OUTPUT_SATISFIES_REQUIREMENT",
        ),
        (
            EffectDescriptor(source="ProducerJoker", kind="JOKER", produces=frozenset({"engine:x"})),
            EffectDescriptor(source="ScalerJoker", kind="JOKER", scales_with=frozenset({"engine:x"})),
            "OUTPUT_FEEDS_SCALING",
        ),
        (
            EffectDescriptor(source="AmplifierJoker", kind="JOKER", amplifies=frozenset({"engine:x"})),
            EffectDescriptor(source="ProducerJoker", kind="JOKER", produces=frozenset({"engine:x"})),
            "AMPLIFIER_TARGETS_OUTPUT",
        ),
    ),
)
def test_behavior_semantics_form_strategy_for_every_generic_relation(
    monkeypatch,
    left: EffectDescriptor,
    right: EffectDescriptor,
    expected_relation: str,
) -> None:
    _Profiler.profile_value = _Profile(left, right)
    monkeypatch.setattr(behavior, "BalatroBuildProfiler", _Profiler)
    devs = (
        BondDevelopment("alpha", True, 2.0, BondRank.R0, 4.0, (BondContribution(left.source.replace("Joker", ""), 2.0),), realization=BondRealization.PARTIAL),
        BondDevelopment("beta", True, 2.0, BondRank.R0, 4.0, (BondContribution(right.source.replace("Joker", ""), 2.0),), realization=BondRealization.PARTIAL),
    )

    candidates = behavior.form_behavior_strategy_candidates(SimpleNamespace(), devs)

    assert candidates
    candidate = candidates[0]
    assert candidate.commitment >= StrategyCommitment.PINNED
    assert any(link.relation == expected_relation for link in candidate.links)


def test_behavior_machine_exposes_missing_requirement_and_scaling_goals(monkeypatch) -> None:
    producer = EffectDescriptor(source="ProducerJoker", kind="JOKER", produces=frozenset({"engine:present"}))
    consumer = EffectDescriptor(
        source="ConsumerJoker",
        kind="JOKER",
        requires=frozenset({"engine:present", "engine:missing_requirement"}),
        scales_with=frozenset({"engine:missing_scale"}),
    )
    _Profiler.profile_value = _Profile(producer, consumer)
    monkeypatch.setattr(behavior, "BalatroBuildProfiler", _Profiler)
    devs = (
        BondDevelopment("alpha", True, 2.0, BondRank.R0, 4.0, (BondContribution("Producer", 2.0),), realization=BondRealization.PARTIAL),
        BondDevelopment("beta", True, 2.0, BondRank.R0, 4.0, (BondContribution("Consumer", 2.0),), realization=BondRealization.PARTIAL),
    )

    candidate = behavior.form_behavior_strategy_candidates(SimpleNamespace(), devs)[0]

    assert "seek_feature:engine:missing_requirement" in candidate.prescriptions
    assert "seek_feature:engine:missing_scale" in candidate.prescriptions
    assert "seek_feature:engine:present" not in candidate.prescriptions


def test_shared_target_can_form_strategy_without_named_pair_table() -> None:
    left = _dev("rank_payoff", "Rank payoff", MechanicalRole.RANK_PAYOFF, target="KINGS")
    right = _dev("support", "King support", MechanicalRole.SUPPORT, target="KINGS")

    candidate = pinned_strategy(form_strategy_candidates((left, right)))

    assert candidate is not None
    assert any(link.relation == "SHARED_MECHANICAL_TARGET" for link in candidate.links)


def test_unrelated_mechanics_do_not_form_false_strategy() -> None:
    left = _dev("cash", "Cash", MechanicalRole.ECONOMY_PAYOFF, target="MONEY")
    right = _dev("straight", "Straight", MechanicalRole.HAND_PAYOFF, target="STRAIGHT")

    assert pinned_strategy(form_strategy_candidates((left, right))) is None
