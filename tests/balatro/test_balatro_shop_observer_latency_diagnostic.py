from types import SimpleNamespace

from games.balatro.shop_observer_latency_diagnostic import (
    _timed_stage,
    shop_decision_latency_note,
)
from games.balatro.shop_policy_latency_diagnostic import (
    _LAST_PROFILE,
    consume_shop_policy_latency_note,
)


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
            "joker_seconds": 1.0,
            "consumable_seconds": 0.4,
            "booster_seconds": 0.5,
            "booster_calls": 2,
            "bond_pair_seconds": 0.8,
            "reroll_seconds": 8.5,
            "reroll_joker_seconds": 8.0,
            "reroll_joker_calls": 1,
        }
    )

    note = consume_shop_policy_latency_note()

    assert note == (
        "shop_d14_latency=total=12.000s "
        "deterministic=0.100s joker=1.000s consumable=0.400s "
        "booster=0.500s/2calls bond_pair=0.800s reroll=8.500s "
        "reroll_joker=8.000s/1calls residual=0.800s"
    )
    assert consume_shop_policy_latency_note() is None
