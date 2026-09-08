import pytest

from games.balatro.live.translator import DefaultBalatroStateTranslator


def test_exact_playing_card_live_id_normalizes_integral_lua_number():
    assert DefaultBalatroStateTranslator._exact_playing_card_live_id(17.0) == 17
    assert type(DefaultBalatroStateTranslator._exact_playing_card_live_id(17.0)) is int


def test_exact_playing_card_live_id_preserves_missing_identity_without_inventing_one():
    assert DefaultBalatroStateTranslator._exact_playing_card_live_id(None) is None


@pytest.mark.parametrize("value", [True, -1, -1.0, 17.5, "17"])
def test_exact_playing_card_live_id_rejects_inexact_or_invalid_identity(value):
    with pytest.raises(ValueError):
        DefaultBalatroStateTranslator._exact_playing_card_live_id(value)
