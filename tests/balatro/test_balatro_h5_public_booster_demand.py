from types import SimpleNamespace

import pytest

import games.balatro.strategy_resource_coherence_policy as resource_policy
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy


class _Profile:
    effects = (
        SimpleNamespace(
            requires=("rank:K",),
            scales_with=(),
            amplifies=(),
        ),
    )
    enhancement_counts = ()
    seal_counts = ()
    edition_counts = ()
    deck_size = 52

    @staticmethod
    def strength(feature: str) -> float:
        del feature
        return 0.0

    @staticmethod
    def can_produce(feature: str) -> bool:
        del feature
        return False


def test_h5_unopened_card_pack_demand_uses_public_build_profile_only():
    policy = BuildAwareShopBoosterPolicy()
    state = SimpleNamespace(jokers=())
    profile = _Profile()

    standard_need, standard_notes = policy._build_need(
        state,
        profile,
        family="STANDARD",
    )
    arcana_need, arcana_notes = policy._build_need(
        state,
        profile,
        family="ARCANA",
    )
    spectral_need, spectral_notes = policy._build_need(
        state,
        profile,
        family="SPECTRAL",
    )

    assert standard_need == pytest.approx(0.25)
    assert arcana_need == pytest.approx(1.0 / 3.0)
    assert spectral_need == pytest.approx(1.0 / 3.0)
    for notes in (standard_notes, arcana_notes, spectral_notes):
        assert any("relevant unmet build features=rank:K" in note for note in notes)
        assert all("strategy relevant" not in note for note in notes)
        assert all("committed/forming strategy" not in note for note in notes)


def test_h5_resource_policy_has_no_strategy_controller_dependency():
    assert not hasattr(resource_policy, "evaluate_bond_composition")
    assert not hasattr(resource_policy, "_strategy_candidate")
    assert not hasattr(resource_policy, "_strategy_features")
    assert not hasattr(resource_policy, "_bond_goal_features")
    assert not hasattr(resource_policy, "_strategy_card_need")


def test_h5_celestial_demand_remains_public_observed_hand_specialization():
    state = SimpleNamespace(
        hand_play_counts={"PAIR": 4},
        hand_levels={"PAIR": 1},
    )

    need, notes = resource_policy._celestial_observed_need(state)

    assert need == pytest.approx(0.8)
    assert any("observed Celestial target hand=PAIR plays=4/4" in note for note in notes)
    assert any("observed hand-play concentration=1.000" in note for note in notes)
    assert all("strategy" not in note.lower() for note in notes)
