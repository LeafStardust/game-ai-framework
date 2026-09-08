from types import SimpleNamespace

from games.balatro.luchador_activation_policy import _should_sell_luchador


class LuchadorJoker:
    area_index = 1


class ChicotJoker:
    area_index = 2


def _state(
    *,
    boss_name="The Needle",
    hands=1,
    discards=4,
    jokers=None,
):
    return SimpleNamespace(
        boss_name=boss_name,
        hands_remaining=hands,
        discards_remaining=discards,
        jokers=list(jokers if jokers is not None else [LuchadorJoker()]),
    )


def _should_sell(state, notes):
    return _should_sell_luchador(state, notes)[0]


def test_luchador_disables_needle_when_d1_is_recovering():
    assert _should_sell(
        _state(),
        ("mode=PACE_RECOVERY", "clear_probability=0.000000"),
    )


def test_luchador_is_preserved_when_d1_has_a_clear_path():
    assert not _should_sell(
        _state(),
        ("mode=CLEAR_PATH", "clear_probability=1.000000"),
    )


def test_luchador_is_preserved_on_ordinary_boss_with_healthy_runway():
    assert not _should_sell(
        _state(boss_name="The Hook", hands=4, discards=4),
        ("mode=PACE_RECOVERY",),
    )


def test_luchador_can_rescue_any_boss_on_last_hand():
    assert _should_sell(
        _state(boss_name="The Hook", hands=1, discards=2),
        ("mode=PACE_RECOVERY",),
    )


def test_luchador_is_not_spent_when_chicot_already_disables_boss():
    assert not _should_sell(
        _state(jokers=[LuchadorJoker(), ChicotJoker()]),
        ("mode=PACE_RECOVERY",),
    )
