from types import SimpleNamespace

from games.balatro.v1_0_0_luchador_policy import _should_sell_luchador


class LuchadorJoker:
    area_index = 0


def _state(boss_name: str, *, hands: int = 4, discards: int = 3):
    return SimpleNamespace(
        boss_name=boss_name,
        hands_remaining=hands,
        discards_remaining=discards,
        jokers=[LuchadorJoker()],
    )


def test_luchador_proactively_disables_suit_debuff_boss_before_recovery():
    assert _should_sell_luchador(
        _state("The Head"),
        ("mode=PACE_PLAY",),
    )
    assert _should_sell_luchador(
        _state("The Window"),
        ("mode=PACE_PLAY",),
    )


def test_luchador_proactively_disables_face_card_debuff_boss():
    assert _should_sell_luchador(
        _state("The Plant"),
        ("mode=PACE_PLAY",),
    )


def test_luchador_keeps_conservative_trigger_for_nonproactive_boss():
    assert not _should_sell_luchador(
        _state("The Wall"),
        ("mode=PACE_PLAY",),
    )
    assert _should_sell_luchador(
        _state("The Wall"),
        ("mode=PACE_RECOVERY",),
    )
