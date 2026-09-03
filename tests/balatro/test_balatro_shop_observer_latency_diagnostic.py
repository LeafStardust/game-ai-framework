from types import SimpleNamespace

from games.balatro.shop_observer_latency_diagnostic import (
    _timed_stage,
    shop_decision_latency_note,
)
from games.balatro.shop_policy_latency_diagnostic import (
    _ACTIVE_PROFILE,
    _LAST_PROFILE,
    consume_shop_policy_latency_note,
    install_shop_policy_latency_diagnostic,
)
from games.balatro.shop_arbiter import BuildAwareShopArbiter


def test_shop_observer_latency_stage_records_without_changing_result():
    owner = SimpleNamespace(_active_shop_latency_profile={})

    result = _timed_stage(owner, "public", lambda: "snapshot")

    assert result == "snapshot"
    assert owner._active_shop_latency_profile["public_calls"] == 1
    assert owner._active_shop_latency_profile["public_seconds"] >= 0.0


def test_shop_decision_latency_note_separates_runner_components():
    runner = SimpleNamespace(
        last_observation_seconds=0.25,
        last_translation_seconds=0.125,
        last_policy_seconds=3.5,
    )

    note = shop_decision_latency_note(runner, 3.875)

    assert note == (
        "shop_decision_latency=total=3.875s "
        "observation=0.250s translation=0.125s policy=3.500s"
    )


def test_shop_d14_latency_note_separates_child_components():
    _LAST_PROFILE.set(
        {
            "total_seconds": 12.0,
            "deterministic_seconds": 0.1,
            "joker_standalone_seconds": 0.7,
            "joker_standalone_calls": 1,
            "joker_seconds": 1.0,
            "consumable_seconds": 0.4,
            "booster_seconds": 0.5,
            "booster_calls": 2,
            "bond_pair_seconds": 0.8,
            "reroll_seconds": 8.5,
            "reroll_visible_seconds": 0.2,
            "reroll_visible_calls": 1,
            "reroll_unmet_seconds": 5.0,
            "reroll_unmet_calls": 1,
            "reroll_future_seconds": 3.2,
            "reroll_future_calls": 1,
            "reroll_future_joker_seconds": 2.5,
            "reroll_future_joker_calls": 1,
            "reroll_future_tarot_seconds": 0.2,
            "reroll_future_tarot_calls": 1,
            "reroll_future_planet_seconds": 0.1,
            "reroll_future_planet_calls": 1,
            "reroll_joker_seconds": 3.0,
            "reroll_joker_calls": 2,
        }
    )

    note = consume_shop_policy_latency_note()

    assert note == (
        "shop_d14_latency=total=12.000s "
        "deterministic=0.100s joker_standalone=0.700s/1calls "
        "joker=1.000s consumable=0.400s "
        "booster=0.500s/2calls bond_pair=0.800s reroll=8.500s "
        "reroll_visible=0.200s/1calls reroll_unmet=5.000s/1calls "
        "reroll_future=3.200s/1calls "
        "reroll_future_joker=2.500s/1calls "
        "reroll_future_tarot=0.200s/1calls "
        "reroll_future_planet=0.100s/1calls "
        "reroll_future_residual=0.400s "
        "reroll_joker=3.000s/2calls residual=0.000s"
    )
    assert consume_shop_policy_latency_note() is None


def test_standalone_joker_evaluation_is_timed_without_changing_results(monkeypatch):
    class Policy:
        @staticmethod
        def decide(state, candidate):
            return state, candidate

    state = SimpleNamespace(shop_jokers=("first", "second"))
    install_shop_policy_latency_diagnostic()
    clock = iter((10.0, 12.5))
    monkeypatch.setattr(
        "games.balatro.shop_policy_latency_diagnostic.perf_counter",
        lambda: next(clock),
    )
    profile = {}
    token = _ACTIVE_PROFILE.set(profile)
    try:
        result = BuildAwareShopArbiter._standalone_joker_decisions(
            state,
            policy=Policy(),
        )
    finally:
        _ACTIVE_PROFILE.reset(token)

    assert result == ((state, "first"), (state, "second"))
    assert profile == {
        "joker_standalone_seconds": 2.5,
        "joker_standalone_calls": 1,
    }


def test_active_deterministic_policy_override_is_timed_as_direct_d14_child(
    monkeypatch,
):
    class Policy:
        @staticmethod
        def rank_actions(state, actions):
            return [state, *actions]

    arbiter = object.__new__(BuildAwareShopArbiter)
    arbiter.shop_policy = Policy()
    install_shop_policy_latency_diagnostic()
    clock = iter((20.0, 23.25))
    monkeypatch.setattr(
        "games.balatro.shop_policy_latency_diagnostic.perf_counter",
        lambda: next(clock),
    )
    profile = {}
    token = _ACTIVE_PROFILE.set(profile)
    try:
        result = arbiter._rank_deterministic_actions("state", ["voucher"])
    finally:
        _ACTIVE_PROFILE.reset(token)

    assert result == ["state", "voucher"]
    assert profile == {
        "deterministic_seconds": 3.25,
        "deterministic_calls": 1,
    }
