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
    constellation = ConstellationJoker()
    constellation.x_mult = 1.4
    lucky = LuckyCatJoker()
    lucky.x_mult = 2.0
    glass = GlassJoker()
    glass.x_mult = 2.5
    vampire = VampireJoker()
    vampire.x_mult = 1.6

    engines = _by_id(_state(constellation, lucky, glass, vampire, ante=4))

    assert engines["constellation"].current_strength == 0.4
    assert engines["lucky_cat"].current_strength == 1.0
    assert engines["glass_joker"].current_strength == 1.5
    assert engines["vampire"].current_strength == 0.6
    assert all(engine.state != EngineState.OWNED_INACTIVE for engine in engines.values())


def test_spare_trousers_and_wee_joker_public_counters_are_realized_scaling():
    trousers = SpareTrousersJoker()
    trousers.mult = 8
    wee = WeeJoker()
    wee.chips = 80

    engines = _by_id(_state(trousers, wee, ante=4))

    assert engines["spare_trousers"].current_strength == 8.0
    assert engines["wee_joker"].current_strength == 80.0
    assert engines["spare_trousers"].state == EngineState.ACTIVATED_HEALTHY
    assert engines["wee_joker"].state == EngineState.ACTIVATED_HEALTHY


def test_owned_but_unscaled_bond_scalers_do_not_create_free_scaling_health():
    engines = _by_id(
        _state(
            ConstellationJoker(),
            LuckyCatJoker(),
            GlassJoker(),
            VampireJoker(),
            SpareTrousersJoker(),
            WeeJoker(),
            ante=5,
        )
    )

    assert engines
    assert all(engine.state == EngineState.OWNED_INACTIVE for engine in engines.values())
