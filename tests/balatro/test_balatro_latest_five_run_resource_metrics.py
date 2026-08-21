from types import SimpleNamespace

import pytest

from games.balatro.latest_five_run_resource_metrics import _celestial_need
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy


def _profile(*, hand_levels, effects=(), deck_size=52, enhancement_counts=(), seal_counts=(), edition_counts=()):
    strengths = {}
    return SimpleNamespace(
        hand_levels=tuple(hand_levels.items()),
        effects=tuple(effects),
        deck_size=deck_size,
        enhancement_counts=tuple(enhancement_counts),
        seal_counts=tuple(seal_counts),
        edition_counts=tuple(edition_counts),
        strength=lambda feature: strengths.get(feature, 0.0),
        can_produce=lambda feature: False,
    )


def test_repeated_level_one_hand_creates_strong_celestial_demand():
    state = SimpleNamespace(hand_play_counts={"TWO_PAIR": 14, "PAIR": 4, "FLUSH": 2})
    profile = _profile(hand_levels={"TWO_PAIR": 1, "PAIR": 1, "FLUSH": 1})

    need, notes = _celestial_need(state, profile)

    assert need > 0.90
    assert any("current TWO_PAIR level=1" in note for note in notes)


def test_celestial_demand_is_small_without_repeated_hand_history():
    state = SimpleNamespace(hand_play_counts={"TWO_PAIR": 1, "PAIR": 1})
    profile = _profile(hand_levels={"TWO_PAIR": 1, "PAIR": 1})

    need, _ = _celestial_need(state, profile)

    assert need < 0.25


def test_existing_hand_levels_reduce_underinvestment_pressure():
    state = SimpleNamespace(hand_play_counts={"TWO_PAIR": 12, "PAIR": 2})
    level_one = _profile(hand_levels={"TWO_PAIR": 1})
    level_four = _profile(hand_levels={"TWO_PAIR": 4})

    weak_need, _ = _celestial_need(state, level_one)
    invested_need, _ = _celestial_need(state, level_four)

    assert weak_need > invested_need


def test_standard_modifier_density_cannot_manufacture_need_without_feature_gap():
    policy = BuildAwareShopBoosterPolicy()
    state = SimpleNamespace()
    profile = _profile(
        hand_levels={},
        deck_size=50,
        enhancement_counts=(("Lucky", 8),),
        seal_counts=(("Blue", 4),),
        edition_counts=(("Holo", 2),),
    )

    need, notes = policy._build_need(state, profile, family="STANDARD")

    assert need == pytest.approx(0.0)
    assert any("cannot manufacture Standard-pack demand" in note for note in notes)


def test_standard_actual_feature_gap_still_creates_positive_need():
    descriptor = SimpleNamespace(
        requires=frozenset({"enhancement:Lucky"}),
        scales_with=frozenset(),
        amplifies=frozenset(),
    )
    policy = BuildAwareShopBoosterPolicy()
    state = SimpleNamespace()
    profile = _profile(hand_levels={}, effects=(descriptor,), deck_size=52)

    need, _ = policy._build_need(state, profile, family="STANDARD")

    assert need > 0.0
