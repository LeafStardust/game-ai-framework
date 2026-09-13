from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _psychic_run(*, seed: str, requirement: int = 9999) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.blind = Blind(BlindType.BOSS, requirement, reward=5)
    state.boss_name = "The Psychic"
    state.hands_remaining = 4
    return deal_supported_round_start(HeadlessRunState(public=state, seed=seed))


def test_env_r4_psychic_under_five_card_play_is_legal_and_scores_zero():
    run = _psychic_run(seed="R4-PSYCHIC-ZERO")
    before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == 0
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert len(result.public.discard_pile) == 1
    assert result.rng_snapshot() == before
    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.public.discard_pile == []


def test_env_r4_psychic_exact_five_card_play_scores_normally_and_can_clear():
    run = _psychic_run(seed="R4-PSYCHIC-CLEAR", requirement=1)

    result = apply_supported_ordinary_play(run, range(5))

    assert result.public.score >= result.public.blind.requirement
    assert result.public.hands_remaining == 3
    assert result.public.phase == "ROUND_EVAL"
    assert len(result.public.hand) == 3
    assert len(result.public.discard_pile) == 5
    assert result.played_pile == []
