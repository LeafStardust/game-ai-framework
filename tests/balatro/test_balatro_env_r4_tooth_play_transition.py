from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.tactical_transition import apply_planned_tactical_step
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _boss_play_run(
    *,
    boss_name="The Tooth",
    seed="R4-TOOTH",
    requirement=9999,
    hands_remaining=4,
    money=0,
):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.blind = Blind(BlindType.BOSS, requirement)
    state.boss_name = boss_name
    state.hands_remaining = hands_remaining
    state.money = money
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


def _card_signature(card):
    return (card.rank, card.suit)


def test_env_r4_tooth_play_applies_press_play_economy_before_scoring_and_redraw():
    run = _boss_play_run(money=0)
    selected = [_card_signature(run.public.hand[index]) for index in (0, 2)]
    rng_before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (2, 0))

    assert result.public.money == -2
    assert result.public.score > 0
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert [_card_signature(card) for card in result.public.discard_pile[-2:]] == selected
    assert result.played_pile == []
    assert result.rng_snapshot() == rng_before

    assert run.public.money == 0
    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.public.discard_pile == []


def test_env_r4_tooth_play_applies_economy_on_blind_clearing_hand():
    run = _boss_play_run(seed="R4-TOOTH-CLEAR", requirement=1, money=0)

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.money == -1
    assert result.public.score >= result.public.blind.requirement
    assert result.public.phase == "ROUND_EVAL"
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == 7
    assert result.played_pile == []


def test_env_r4_tooth_play_applies_economy_on_final_hand_loss():
    run = _boss_play_run(
        seed="R4-TOOTH-LOSS",
        requirement=9999,
        hands_remaining=1,
        money=1,
    )

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.money == 0
    assert result.public.score < result.public.blind.requirement
    assert result.public.phase == "GAME_OVER"
    assert result.public.hands_remaining == 0
    assert len(result.public.hand) == 7
    assert result.played_pile == []


def test_env_r4_unowned_boss_play_remains_fail_closed():
    run = _boss_play_run(boss_name="The Wall", seed="R4-WALL-CLOSED")
    rng_before = run.rng_snapshot()

    with pytest.raises(
        HeadlessTransitionError,
        match="Small/Big blinds, The Tooth, and The Hook only",
    ):
        apply_supported_ordinary_play(run, (0,))

    assert run.public.money == 0
    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.rng_snapshot() == rng_before


class _ToothPlayDecisionEngine:
    def __init__(self):
        self.observation = None

    def decide(self, state):
        self.observation = state
        return SimpleNamespace(
            action=BalatroAction(
                PLAY_CARDS,
                cards=[state.hand[0], state.hand[1]],
            )
        )


def test_env_r4_decision_engine_bridge_executes_exact_tooth_play():
    run = _boss_play_run(seed="R4-TOOTH-BRIDGE", money=3)
    decision_engine = _ToothPlayDecisionEngine()

    result = apply_planned_tactical_step(run, decision_engine)

    assert result.public.money == 1
    assert result.public.score > 0
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert decision_engine.observation is not run.public
    assert decision_engine.observation.boss_name == "The Tooth"
