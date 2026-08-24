from types import SimpleNamespace

from games.balatro.build_health import EngineState
from games.balatro.jokers.campfire import CampfireJoker
from games.balatro.jokers.flash_card import FlashCardJoker
from games.balatro.jokers.hiker import HikerJoker
from games.balatro.jokers.obelisk import ObeliskJoker
from games.balatro.state import BalatroState
from games.balatro.tactical_scaler_build_health import _tactical_scaler_engines


def _state(*jokers, ante: int = 4, money: int = 20):
    state = BalatroState()
    state.ante = ante
    state.money = money
    state.jokers = list(jokers)
    return state


def _by_id(state):
    return {engine.engine_id: engine for engine in _tactical_scaler_engines(state)}


def test_campfire_realized_xmult_is_visible_without_becoming_a_bond():
    campfire = CampfireJoker()
    campfire.x_mult = 2.0
    engine = _by_id(_state(campfire, ante=4))["campfire"]
    assert engine.current_strength == 1.0
    assert engine.state in {EngineState.ACTIVATED_HEALTHY, EngineState.MATURE}
    assert engine.growth_rate > 0.0
    assert any("resets after each Boss Blind" in note for note in engine.rationale)


def test_flash_card_uses_only_realized_mult_and_cash_only_affects_growth_rate():
    flash = FlashCardJoker()
    flash.mult = 8
    poor = _by_id(_state(flash, ante=4, money=4))["flash_card"]
    rich = _by_id(_state(flash, ante=4, money=30))["flash_card"]
    assert poor.current_strength == rich.current_strength == 8.0
    assert poor.state == rich.state
    assert rich.growth_rate > poor.growth_rate


def test_obelisk_public_xmult_is_visible_but_keeps_brittle_runway_cost():
    obelisk = ObeliskJoker()
    obelisk.x_mult = 1.8
    engine = _by_id(_state(obelisk, ante=4))["obelisk"]
    assert engine.current_strength == 0.8
    assert engine.state != EngineState.OWNED_INACTIVE
    assert engine.runway_need > 0.0
    assert any("resets when the most-played hand is used" in note for note in engine.rationale)


def test_red_card_accumulated_mult_is_realized_tactical_scaling():
    red_card = SimpleNamespace(label="Red Card", mult=12)
    engine = _by_id(_state(red_card, ante=4))["red_card"]
    assert engine.current_strength == 12.0
    assert engine.state in {EngineState.ACTIVATED_HEALTHY, EngineState.MATURE}
    assert any("future booster skips are not pre-credited" in note for note in engine.rationale)


def test_hiker_counts_only_already_written_public_permanent_card_growth():
    state = _state(HikerJoker(), ante=4)
    state.owned_deck = [
        SimpleNamespace(permanent_bonus=20),
        SimpleNamespace(permanent_bonus=15),
        SimpleNamespace(permanent_bonus=5),
        SimpleNamespace(permanent_bonus=0),
    ]
    engine = _by_id(state)["hiker_card_growth"]
    assert engine.current_strength == 40.0
    assert engine.state == EngineState.ACTIVATED_HEALTHY
    assert any("trained permanent cards=3/4" in note for note in engine.rationale)


def test_unscaled_nonbond_scalers_remain_inactive_not_free_power():
    state = _state(CampfireJoker(), FlashCardJoker(), ObeliskJoker(), HikerJoker(), SimpleNamespace(label="Red Card", mult=0), ante=5)
    state.owned_deck = [SimpleNamespace(permanent_bonus=0)]
    engines = _by_id(state)
    assert engines["campfire"].state == EngineState.OWNED_INACTIVE
    assert engines["flash_card"].state == EngineState.OWNED_INACTIVE
    assert engines["obelisk"].state == EngineState.OWNED_INACTIVE
    assert engines["red_card"].state == EngineState.OWNED_INACTIVE
    assert engines["hiker_card_growth"].state == EngineState.OWNED_INACTIVE
