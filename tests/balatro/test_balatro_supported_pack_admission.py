from types import SimpleNamespace

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.shop_booster_policy import BUY, BuildAwareShopBoosterPolicy
from games.balatro.state import BalatroState


def _shop_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 50
    state.ante = 1
    return state


def test_arcana_pack_can_be_admitted_when_d8_value_clears_thresholds():
    state = _shop_state()
    pack = SimpleNamespace(label="Arcana Pack", cost=0)

    result = BuildAwareShopBoosterPolicy().recommend(
        state,
        BalatroAction(BUY_BOOSTER, target=pack),
    )

    assert result.family == "ARCANA"
    assert result.at_least_one_hit_probability >= 0.45
    assert result.advantage_over_save > 0.35
    assert result.decision == BUY
    assert any("autonomous-safe" in note for note in result.rationale)


def test_mega_spectral_pack_can_be_admitted_when_d8_value_clears_thresholds():
    state = _shop_state()
    pack = SimpleNamespace(label="Mega Spectral Pack", cost=0)

    result = BuildAwareShopBoosterPolicy().recommend(
        state,
        BalatroAction(BUY_BOOSTER, target=pack),
    )

    assert result.family == "SPECTRAL"
    assert result.at_least_one_hit_probability >= 0.45
    assert result.advantage_over_save > 0.35
    assert result.decision == BUY
    assert any("autonomous-safe" in note for note in result.rationale)
