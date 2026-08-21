from types import SimpleNamespace

from games.balatro.noncash_cash_deployment_policy import (
    cash_scaling_active,
    deployment_reserve,
    deployment_reroll_limit,
    weak_build_for_cash_deployment,
)


def _joker(name):
    return SimpleNamespace(name=name, label=name)


def test_bull_and_bootstraps_exempt_cash_from_deployment():
    bull = SimpleNamespace(jokers=[_joker("Bull")])
    bootstraps = SimpleNamespace(jokers=[_joker("Bootstraps")])
    ordinary = SimpleNamespace(jokers=[_joker("Misprint")])

    assert cash_scaling_active(None, bull) is True
    assert cash_scaling_active(None, bootstraps) is True
    assert cash_scaling_active(None, ordinary) is False


def test_only_materially_weak_builds_deploy_excess_cash():
    healthy = SimpleNamespace(
        scaling_deficit=False,
        survival=90.0,
        immediate=85.0,
    )
    survival_weak = SimpleNamespace(
        scaling_deficit=False,
        survival=70.0,
        immediate=85.0,
    )
    immediate_weak = SimpleNamespace(
        scaling_deficit=False,
        survival=90.0,
        immediate=65.0,
    )
    scaling_weak = SimpleNamespace(
        scaling_deficit=True,
        survival=90.0,
        immediate=85.0,
    )

    assert weak_build_for_cash_deployment(healthy) is False
    assert weak_build_for_cash_deployment(survival_weak) is True
    assert weak_build_for_cash_deployment(immediate_weak) is True
    assert weak_build_for_cash_deployment(scaling_weak) is True


def test_cash_deployment_keeps_small_emergency_reserve_and_is_bounded():
    assert deployment_reserve(1) == 3
    assert deployment_reserve(2) == 3
    assert deployment_reserve(3) == 5
    assert deployment_reserve(7) == 5

    assert deployment_reroll_limit(24) == 1
    assert deployment_reroll_limit(25) == 2
    assert deployment_reroll_limit(40) == 2
