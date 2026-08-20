from types import SimpleNamespace

from games.balatro.build_health import EngineState
from games.balatro.build_health_runtime import (
    RealizedEngineAnalyzer,
    RuntimeBuildHealthEvaluator,
    projected_state_with_jokers,
)
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.certificate import CertificateJoker
from games.balatro.jokers.hologram import HologramJoker
from games.balatro.state import BalatroState


class _FixedScorer:
    def __init__(self, total):
        self.total = float(total)

    def score(self, *args, **kwargs):
        del args, kwargs
        return SimpleNamespace(total=self.total)


def _state(*, ante=1, blind_score=600, hands=4, jokers=()):
    state = BalatroState()
    state.ante = ante
    state.blind_score = blind_score
    state.hands_remaining = hands
    state.jokers = list(jokers)
    return state


def test_hologram_owned_at_base_xmult_is_explicitly_inactive():
    hologram = HologramJoker()
    state = _state(ante=4, blind_score=5000, jokers=(hologram,))

    engine = RealizedEngineAnalyzer().analyze(state)[0]

    assert engine.engine_id == "hologram"
    assert engine.state == EngineState.OWNED_INACTIVE
    assert engine.current_strength == 1.0
    assert engine.runway_need > 0.5


def test_hologram_public_growth_changes_realized_engine_state():
    hologram = HologramJoker()
    hologram.x_mult = 1.5
    state = _state(ante=3, blind_score=2000, jokers=(hologram,))

    engine = RealizedEngineAnalyzer().analyze(state)[0]

    assert engine.state in {EngineState.ACTIVATED_HEALTHY, EngineState.MATURE}
    assert engine.current_strength == 1.5


def test_blue_joker_card_generator_realizes_future_growth_capacity():
    blue = BlueJoker()
    without_generator = _state(ante=4, blind_score=5000, jokers=(blue,))
    with_generator = _state(
        ante=4,
        blind_score=5000,
        jokers=(BlueJoker(), CertificateJoker()),
    )

    base = next(
        engine
        for engine in RealizedEngineAnalyzer().analyze(without_generator)
        if engine.engine_id == "blue_joker"
    )
    activated = next(
        engine
        for engine in RealizedEngineAnalyzer().analyze(with_generator)
        if engine.engine_id == "blue_joker"
    )

    assert activated.current_strength == base.current_strength
    assert activated.growth_rate == 1.0
    assert activated.growth_rate > base.growth_rate
    assert any("card generator owned=yes" in note for note in activated.rationale)


def test_cash_scoring_is_immediately_mature_when_existing_cash_already_realizes_it():
    state = _state(
        ante=5,
        blind_score=16500,
        jokers=(BullJoker(), BootstrapsJoker()),
    )
    state.money = 50

    engines = RealizedEngineAnalyzer().analyze(state)
    cash = next(engine for engine in engines if engine.engine_id == "cash_scoring")

    assert cash.state == EngineState.MATURE
    assert cash.runway_need == 0.0
    assert cash.current_strength > 0.0


def test_midgame_static_board_reports_scaling_deficit_when_immediate_output_is_adequate():
    state = _state(ante=4, blind_score=5000, hands=4)
    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(1500)).evaluate(state)

    assert health.immediate == 100.0
    assert health.survival == 100.0
    assert health.scaling < 50.0
    assert health.scaling_deficit


def test_foundation_without_scaler_is_not_prematurely_called_scaling_deficit():
    state = _state(ante=2, blind_score=800, hands=4)
    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(300)).evaluate(state)

    assert health.immediate == 100.0
    assert health.scaling >= 50.0
    assert not health.scaling_deficit


def test_projected_joker_roster_does_not_mutate_live_state():
    original = HologramJoker()
    candidate = BullJoker()
    state = _state(jokers=(original,))

    projected = projected_state_with_jokers(state, (original, candidate))

    assert state.jokers == [original]
    assert projected.jokers == [original, candidate]
    assert projected is not state
