from types import SimpleNamespace

import pytest

from games.balatro.bond_scaler_build_health_policy import _bond_scaler_engines
from games.balatro.build_health import EngineState
from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.jokers.spare_trousers import SpareTrousersJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.jokers.wee_joker import WeeJoker
from games.balatro.state import BalatroState


def _state(*jokers, ante: int = 4):
    state = BalatroState()
    state.ante = ante
    state.jokers = list(jokers)
    return state


def _by_id(state):
    return {engine.engine_id: engine for engine in _bond_scaler_engines(state)}


def test_xmult_bond_scalers_use_only_current_public_accumulation():
    constellation = ConstellationJoker(); constellation.x_mult = 1.4
    lucky = LuckyCatJoker(); lucky.x_mult = 2.0
    glass = GlassJoker(); glass.x_mult = 2.5
    vampire = VampireJoker(); vampire.x_mult = 1.6
    engines = _by_id(_state(constellation, lucky, glass, vampire, ante=4))
    assert engines["constellation"].current_strength == pytest.approx(0.4)
    assert engines["lucky_cat"].current_strength == pytest.approx(1.0)
    assert engines["glass_joker"].current_strength == pytest.approx(1.5)
    assert engines["vampire"].current_strength == pytest.approx(0.6)
    assert all(engine.state != EngineState.OWNED_INACTIVE for engine in engines.values())


def test_spare_trousers_and_wee_joker_public_counters_are_realized_scaling():
    trousers = SpareTrousersJoker(); trousers.mult = 8
    wee = WeeJoker(); wee.chips = 80
    engines = _by_id(_state(trousers, wee, ante=4))
    assert engines["spare_trousers"].current_strength == 8.0
    assert engines["wee_joker"].current_strength == 80.0
    assert engines["spare_trousers"].state == EngineState.ACTIVATED_HEALTHY
    assert engines["wee_joker"].state == EngineState.ACTIVATED_HEALTHY


def test_green_supernova_and_ride_public_mult_are_realized_scaling():
    green = SimpleNamespace(label="Green Joker", mult=8)
    supernova = SimpleNamespace(label="Supernova", mult=10)
    ride = SimpleNamespace(label="Ride the Bus", mult=12)
    engines = _by_id(_state(green, supernova, ride, ante=4))
    assert engines["green_joker"].current_strength == 8.0
    assert engines["supernova"].current_strength == 10.0
    assert engines["ride_the_bus"].current_strength == 12.0
    assert all(engine.state != EngineState.OWNED_INACTIVE for engine in engines.values())
    assert engines["green_joker"].runway_need > engines["supernova"].runway_need


def test_owned_but_unscaled_bond_scalers_do_not_create_free_scaling_health():
    engines = _by_id(
        _state(
            ConstellationJoker(), LuckyCatJoker(), GlassJoker(), VampireJoker(),
            SpareTrousersJoker(), WeeJoker(),
            SimpleNamespace(label="Green Joker", mult=0),
            SimpleNamespace(label="Supernova", mult=0),
            SimpleNamespace(label="Ride the Bus", mult=0),
            ante=5,
        )
    )
    assert engines
    assert all(engine.state == EngineState.OWNED_INACTIVE for engine in engines.values())
