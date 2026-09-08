from types import SimpleNamespace

from games.balatro.build_health import EngineState
from games.balatro.build_health_runtime import (
    RealizedEngineAnalyzer,
    RuntimeBuildHealthEvaluator,
    projected_state_with_jokers,
)
from games.balatro.card import BalatroCard
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.certificate import CertificateJoker
from games.balatro.jokers.hologram import HologramJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.state import BalatroState


class _FixedScorer:
    def __init__(self, total):
        self.total = float(total)

    def score(self, *args, **kwargs):
        del args, kwargs
        return SimpleNamespace(total=self.total)


class _DeckLengthScorer:
    def score(self, hand, *, state, cards, resolve_random_effects):
        del hand, cards, resolve_random_effects
        return SimpleNamespace(total=float(len(state.deck)))


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


def test_duplicate_holograms_multiply_realized_xmult():
    first = HologramJoker()
    second = HologramJoker()
    first.x_mult = 1.5
    second.x_mult = 2.0
    state = _state(ante=4, blind_score=5000, jokers=(first, second))
    engine = next(value for value in RealizedEngineAnalyzer().analyze(state) if value.engine_id == "hologram")
    assert engine.current_strength == 3.0
    assert any("copies=2" in note for note in engine.rationale)


def test_blue_joker_card_generator_realizes_future_growth_capacity():
    blue = BlueJoker()
    without_generator = _state(ante=4, blind_score=5000, jokers=(blue,))
    with_generator = _state(ante=4, blind_score=5000, jokers=(BlueJoker(), CertificateJoker()))
    base = next(engine for engine in RealizedEngineAnalyzer().analyze(without_generator) if engine.engine_id == "blue_joker")
    activated = next(engine for engine in RealizedEngineAnalyzer().analyze(with_generator) if engine.engine_id == "blue_joker")
    assert activated.current_strength == base.current_strength
    assert activated.growth_rate == 1.0
    assert activated.growth_rate > base.growth_rate
    assert any("card generator owned=yes" in note for note in activated.rationale)


def test_blue_uses_remaining_draw_pile_in_blind_and_post_opening_owned_deck_in_shop():
    state = _state(ante=4, blind_score=5000, jokers=(BlueJoker(),))
    state.owned_deck = [BalatroCard("A", "Spades") for _ in range(52)]
    state.deck = [BalatroCard("A", "Spades") for _ in range(40)]
    state.phase = "SELECTING_HAND"
    active = next(engine for engine in RealizedEngineAnalyzer().analyze(state) if engine.engine_id == "blue_joker")
    state.phase = "SHOP"
    shop = next(engine for engine in RealizedEngineAnalyzer().analyze(state) if engine.engine_id == "blue_joker")
    assert active.current_strength == 80.0
    assert shop.current_strength == 88.0


def test_blue_normal_growth_baseline_tracks_modified_hand_size():
    state = _state(ante=4, blind_score=5000, jokers=(BlueJoker(),))
    state.phase = "SHOP"
    state.hand_size = 10
    state.owned_deck = [BalatroCard("A", "Spades") for _ in range(52)]

    engine = next(
        value
        for value in RealizedEngineAnalyzer().analyze(state)
        if value.engine_id == "blue_joker"
    )

    assert engine.current_strength == 84.0
    assert engine.growth_rate == 0.50
    assert any("remainder=42" in note and "hand size 10" in note for note in engine.rationale)


def test_shop_scoring_probe_uses_post_opening_owned_deck_without_hidden_order():
    state = _state(ante=4, blind_score=5000)
    state.phase = "SHOP"
    state.owned_deck = [BalatroCard("A", "Spades") for _ in range(52)]
    state.deck = []
    evaluator = RuntimeBuildHealthEvaluator(scorer=_DeckLengthScorer())
    assert evaluator._representative_best_score(state) == 44.0


def test_shop_scoring_probe_tracks_modified_hand_size():
    state = _state(ante=4, blind_score=5000)
    state.phase = "SHOP"
    state.hand_size = 10
    state.owned_deck = [BalatroCard("A", "Spades") for _ in range(52)]
    state.deck = []
    evaluator = RuntimeBuildHealthEvaluator(scorer=_DeckLengthScorer())
    assert evaluator._representative_best_score(state) == 42.0


def test_duplicate_blue_jokers_stack_chip_contribution():
    state = _state(ante=4, blind_score=5000, jokers=(BlueJoker(), BlueJoker()))
    state.phase = "SHOP"
    state.owned_deck = [BalatroCard("A", "Spades") for _ in range(52)]
    engine = next(value for value in RealizedEngineAnalyzer().analyze(state) if value.engine_id == "blue_joker")
    assert engine.current_strength == 176.0


def test_runner_growth_history_counts_straight_flushes_too():
    state = _state(ante=4, blind_score=5000, jokers=(RunnerJoker(),))
    state.jokers[0].chips = 30
    state.hand_play_counts["STRAIGHT"] = 1
    state.hand_play_counts["STRAIGHT_FLUSH"] = 1

    engine = next(
        value
        for value in RealizedEngineAnalyzer().analyze(state)
        if value.engine_id == "runner"
    )

    assert engine.growth_rate == 0.25
    assert any("history=2" in note for note in engine.rationale)


def test_burnt_growth_requires_first_discard_to_still_be_available_mid_blind():
    state = _state(ante=4, blind_score=5000, jokers=(BurntJoker(),))
    state.phase = "SELECTING_HAND"
    state.discards_remaining = 2
    state.discards_used = 0
    available = next(
        value
        for value in RealizedEngineAnalyzer().analyze(state)
        if value.engine_id == "burnt_joker"
    )

    state.discards_used = 1
    spent = next(
        value
        for value in RealizedEngineAnalyzer().analyze(state)
        if value.engine_id == "burnt_joker"
    )

    assert available.growth_rate == 1.0
    assert spent.growth_rate == 0.50
    assert any("available now/next=no" in note for note in spent.rationale)


def test_burnt_shop_projection_restores_next_round_first_discard_opportunity():
    state = _state(ante=4, blind_score=5000, jokers=(BurntJoker(),))
    state.phase = "SHOP"
    state.discards_remaining = 0
    state.discards_used = 3

    engine = next(
        value
        for value in RealizedEngineAnalyzer().analyze(state)
        if value.engine_id == "burnt_joker"
    )

    assert engine.growth_rate == 1.0


def test_cash_scoring_is_immediately_mature_when_existing_cash_already_realizes_it():
    state = _state(ante=5, blind_score=16500, jokers=(BullJoker(), BootstrapsJoker()))
    state.money = 50
    engines = RealizedEngineAnalyzer().analyze(state)
    cash = next(engine for engine in engines if engine.engine_id == "cash_scoring")
    assert cash.state == EngineState.MATURE
    assert cash.runway_need == 0.0
    assert cash.current_strength == 50.0


def test_duplicate_cash_scorers_keep_chip_and_mult_outputs_in_separate_units():
    state = _state(
        ante=5,
        blind_score=16500,
        jokers=(BullJoker(), BullJoker(), BootstrapsJoker(), BootstrapsJoker()),
    )
    state.money = 50
    cash = next(engine for engine in RealizedEngineAnalyzer().analyze(state) if engine.engine_id == "cash_scoring")
    assert cash.current_strength == 50.0
    assert any("Bull copies=2" in note and "+200 chips" in note for note in cash.rationale)
    assert any("Bootstraps copies=2" in note and "+40 Mult" in note for note in cash.rationale)


def test_midgame_static_board_reports_scaling_deficit_when_immediate_output_is_adequate():
    state = _state(ante=4, blind_score=5000, hands=4)
    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(1500)).evaluate(state)
    assert health.immediate == 100.0
    assert health.survival == 100.0
    assert health.scaling < 50.0
    assert health.scaling_deficit


def test_mid_blind_survival_uses_remaining_chips_not_original_target():
    state = _state(ante=4, blind_score=5000, hands=2)
    state.phase = "SELECTING_HAND"
    state.score = 4000
    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(500)).evaluate(state)
    assert health.survival == 100.0
    assert health.immediate == 100.0


def test_shop_survival_does_not_subtract_completed_blind_score_from_proxy_target():
    state = _state(ante=4, blind_score=5000, hands=0)
    state.phase = "SHOP"
    state.score = 6000
    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(500)).evaluate(state)
    assert health.survival == 40.0
    assert health.immediate == 40.0


def test_lost_terminal_state_cannot_report_perfect_survival():
    state = _state(ante=4, blind_score=10000, hands=0)
    state.phase = "GAME_OVER"
    state.score = 4640

    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(50000)).evaluate(state)

    assert health.survival == 0.0
    assert health.immediate == 0.0
    assert health.critical


def test_solo_mature_green_joker_does_not_masquerade_as_complete_scaling():
    green = SimpleNamespace(name="Green Joker", mult=14)
    state = _state(ante=4, blind_score=10000, hands=4, jokers=(green,))

    health = RuntimeBuildHealthEvaluator(scorer=_FixedScorer(3000)).evaluate(state)

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
