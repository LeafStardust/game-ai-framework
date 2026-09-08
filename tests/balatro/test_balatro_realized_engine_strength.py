from types import SimpleNamespace

from games.balatro.build_health import EngineState
from games.balatro.realized_engine_strength import RealizedEngineObserver


def _joker(name, **fields):
    return SimpleNamespace(name=name, **fields)


def _state(*, jokers=(), money=0, blind=1000, deck_size=52):
    return SimpleNamespace(
        jokers=list(jokers),
        money=money,
        blind_requirement=blind,
        owned_deck=[object()] * deck_size,
        deck=[object()] * deck_size,
    )


def _engine(state, engine_id):
    return next(
        engine
        for engine in RealizedEngineObserver().observe(state)
        if engine.engine_id == engine_id
    )


def test_hologram_x1_is_owned_inactive_even_when_catalogue_synergy_exists():
    state = _state(jokers=(_joker("Hologram", x_mult=1.0), _joker("Certificate")))
    engine = _engine(state, "hologram_deck_growth")
    assert engine.state is EngineState.OWNED_INACTIVE
    assert engine.growth_rate > 0.0


def test_hologram_reports_realized_growth_from_public_xmult():
    state = _state(jokers=(_joker("Hologram", x_mult=2.5), _joker("Certificate")), deck_size=62)
    engine = _engine(state, "hologram_deck_growth")
    assert engine.state in {EngineState.ACTIVATED_HEALTHY, EngineState.MATURE}
    assert engine.current_strength == 2.5


def test_blue_joker_is_functional_without_generator_but_reports_generator_runway():
    state = _state(jokers=(_joker("Blue Joker"),), deck_size=52)
    engine = _engine(state, "blue_joker_deck_size")
    assert engine.state is not EngineState.OWNED_INACTIVE
    assert engine.current_strength == 52.0
    assert engine.growth_rate == 0.0


def test_mutable_scaler_uses_observed_public_progress():
    state = _state(jokers=(_joker("Castle", chips=3, chip_mod=3, suit="Diamonds"),), blind=3000)
    engine = _engine(state, "castle")
    assert engine.current_strength == 3.0
    assert engine.state is EngineState.ACTIVATED_WEAK


def test_bull_bootstraps_maturity_comes_from_current_cash_output_not_fixed_cash_gate():
    low = _state(jokers=(_joker("Bull"), _joker("Bootstraps")), money=5, blind=20000)
    high = _state(jokers=(_joker("Bull"), _joker("Bootstraps")), money=80, blind=20000)
    low_engine = _engine(low, "bull_bootstraps_cash")
    high_engine = _engine(high, "bull_bootstraps_cash")
    assert high_engine.current_strength > low_engine.current_strength
    assert high_engine.runway_need < low_engine.runway_need


def test_unowned_engines_are_not_fabricated():
    assert RealizedEngineObserver().observe(_state()) == ()
