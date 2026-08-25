from types import SimpleNamespace

import pytest

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND
from games.balatro.blind_skip_policy import (
    BlindSkipThresholds,
    BuildAwareBlindSkipPolicy,
)
from games.balatro.build.effects import SCORE_CHIPS, SCORE_MULT, SCORE_XMULT
from games.balatro.build.profile import BuildProfile
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Profiler:
    def __init__(self, profile):
        self.profile_value = profile

    def profile(self, state):
        del state
        return self.profile_value


def _profile(*, money=0, ante=1, ready=False, prospective_scoring=False):
    if ready:
        free_joker_slots = 0
        hand_levels = (("PAIR", 7),)
        effects = (
            SimpleNamespace(produces={SCORE_CHIPS}),
            SimpleNamespace(produces={SCORE_MULT}),
            SimpleNamespace(produces={SCORE_XMULT}),
        )
        feature_strengths = (
            (SCORE_CHIPS, 1.0),
            (SCORE_MULT, 1.0),
            (SCORE_XMULT, 1.0),
        )
    else:
        free_joker_slots = 5
        hand_levels = (("PAIR", 1),)
        effects = (
            (SimpleNamespace(produces={SCORE_MULT}),)
            if prospective_scoring
            else ()
        )
        feature_strengths = ()

    return BuildProfile(
        money=money,
        ante=ante,
        joker_slots=5,
        free_joker_slots=free_joker_slots,
        consumable_slots=2,
        free_consumable_slots=2,
        deck_size=52,
        rank_counts=(),
        suit_counts=(),
        enhancement_counts=(),
        seal_counts=(),
        edition_counts=(),
        hand_levels=hand_levels,
        joker_names=(),
        consumable_names=(),
        effects=effects,
        feature_strengths=feature_strengths,
    )


def _state(*, money=0, hand_plays=0):
    return SimpleNamespace(
        money=money,
        joker_slots=5,
        jokers=[],
        hand_play_counts={"PAIR": hand_plays},
        blind=None,
    )


def _snapshot(*, blind_type="SMALL", tag="tag_rare", reward=0, money=0):
    return LiveBalatroSnapshot(
        sequence=1,
        phase="BLIND_SELECT",
        state_complete=True,
        payload={
            "money": money,
            "blind": {
                "type": blind_type,
                "tag": tag,
                "reward": reward,
            },
        },
    )


def _policy(profile):
    return BuildAwareBlindSkipPolicy(profiler=_Profiler(profile))


def test_investment_tag_clearly_beats_early_small_blind_development_value():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(tag="tag_investment", reward=3),
        _state(),
    )

    assert decision.action_name == SKIP_BLIND
    assert decision.tag_ev == 25.0
    assert decision.margin > decision.threshold


def test_rare_tag_does_not_override_weak_build_need_for_shop_access():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(tag="tag_rare", reward=3),
        _state(),
    )

    assert decision.action_name == SELECT_BLIND
    assert decision.shop_opportunity_cost > decision.tag_build_adjustment
    assert decision.margin < decision.threshold


def test_negative_tag_can_justify_small_blind_skip_for_weak_build():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(tag="tag_negative", reward=3),
        _state(),
    )

    assert decision.action_name == SKIP_BLIND
    assert decision.tag_build_adjustment > 0.0


def test_big_blind_skip_pays_explicit_pre_boss_preparation_cost():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(blind_type="BIG", tag="tag_negative", reward=4),
        _state(),
    )

    assert decision.action_name == SELECT_BLIND
    assert decision.boss_preparation_cost > 0.0
    assert decision.play_ev > decision.skip_ev


def test_economy_tag_scales_from_public_cash_and_can_justify_skip():
    policy = _policy(_profile(money=20))

    decision = policy.decide(
        _snapshot(tag="tag_economy", reward=3, money=20),
        _state(money=20),
    )

    assert decision.action_name == SKIP_BLIND
    assert decision.tag_ev == 20.0
    assert decision.interest_opportunity_cost == 4.0


def test_strong_build_values_lost_shop_less_than_developing_build():
    weak = _policy(_profile()).decide(
        _snapshot(tag="tag_rare", reward=3),
        _state(),
    )
    strong = _policy(
        _profile(ready=True),
    ).decide(
        _snapshot(tag="tag_rare", reward=3),
        _state(),
    )

    assert weak.build_readiness == pytest.approx(0.0)
    assert strong.build_readiness == pytest.approx(1.0)
    assert strong.shop_opportunity_cost < weak.shop_opportunity_cost


def test_prospective_scoring_descriptor_does_not_inflate_build_readiness():
    decision = _policy(
        _profile(prospective_scoring=True),
    ).decide(
        _snapshot(tag="tag_rare", reward=3),
        _state(),
    )

    assert decision.build_readiness == pytest.approx(0.0)


def test_handy_tag_uses_public_run_hand_count_when_it_exceeds_fallback():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(tag="tag_handy", reward=3),
        _state(hand_plays=12),
    )

    assert decision.tag_ev == 12.0
    assert decision.tag_value_source == "observed_live_tag:tag_handy"


def test_boss_blind_is_never_skipped_even_for_extreme_tag_value():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(blind_type="BOSS", tag="tag_investment", reward=5),
        _state(),
    )

    assert decision.action_name == SELECT_BLIND


def test_observed_blind_reward_is_used_in_play_ev_and_logged_source():
    policy = _policy(_profile())

    decision = policy.decide(
        _snapshot(tag="tag_rare", reward=7),
        _state(),
    )

    assert decision.blind_reward_ev == 7.0
    assert decision.blind_reward_source == "observed_live_blind_reward"
    assert decision.play_ev >= 7.0


def test_d13_threshold_mapping_rejects_unknown_configuration():
    with pytest.raises(ValueError, match="unknown D13 blind-skip threshold"):
        BlindSkipThresholds.from_mapping({"not_a_d13_threshold": 1})
