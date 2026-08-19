from types import SimpleNamespace

from games.balatro.shop_regression_policy import (
    BASEBALL_MIN_UNCOMMON_SUPPORT,
    baseball_uncommon_support,
    burnt_engine_bonus,
)


def _joker(rarity):
    return SimpleNamespace(rarity=rarity)


def test_baseball_requires_established_uncommon_core():
    state = SimpleNamespace(jokers=[])
    assert baseball_uncommon_support(state) == 0
    assert baseball_uncommon_support(state) < BASEBALL_MIN_UNCOMMON_SUPPORT

    state.jokers.append(_joker("UNCOMMON"))
    assert baseball_uncommon_support(state) == 1
    assert baseball_uncommon_support(state) < BASEBALL_MIN_UNCOMMON_SUPPORT

    state.jokers.append(_joker("uncommon"))
    assert baseball_uncommon_support(state) == BASEBALL_MIN_UNCOMMON_SUPPORT


def test_baseball_support_ignores_non_uncommon_jokers():
    state = SimpleNamespace(
        jokers=[_joker("COMMON"), _joker("RARE"), _joker("LEGENDARY")]
    )
    assert baseball_uncommon_support(state) == 0


def test_burnt_engine_value_is_front_loaded_but_never_zero():
    early = burnt_engine_bonus(SimpleNamespace(ante=2))
    late = burnt_engine_bonus(SimpleNamespace(ante=7))

    assert early > late
    assert late >= 2.5
