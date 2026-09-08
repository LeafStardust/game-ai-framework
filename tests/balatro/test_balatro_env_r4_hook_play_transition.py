from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_play import apply_hook_press_play_discards
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.tactical_transition import apply_planned_tactical_step
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _hook_play_run(
    *,
    seed="R4-HOOK",
    requirement=9999,
    hands_remaining=4,
):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.blind = Blind(BlindType.BOSS, requirement)
    state.boss_name = "The Hook"
    state.hands_remaining = hands_remaining
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


def _card_signature(card):
    return (card.rank, card.suit)


def _expected_hook_press_play(run, indices):
    action = BalatroAction(
        PLAY_CARDS,
        cards=[run.public.hand[index] for index in indices],
    )
    result = apply_hook_press_play_discards(run, action)
    return (
        [_card_signature(card) for card in result.public.discard_pile],
        result.rng_snapshot(),
    )


def test_env_r4_hook_play_composes_forced_discards_before_scoring_and_redraw():
    run = _hook_play_run(seed="R4-HOOK-CONTINUE")
    selected_indices = (0, 2)
    selected = [_card_signature(run.public.hand[index]) for index in selected_indices]
    forced, expected_rng = _expected_hook_press_play(run, selected_indices)
    rng_before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (2, 0))

    assert len(forced) == 2
    assert not set(forced).intersection(selected)
    assert [_card_signature(card) for card in result.public.discard_pile[:2]] == forced
    assert [_card_signature(card) for card in result.public.discard_pile[-2:]] == selected
    assert result.rng_snapshot() == expected_rng
    assert result.rng_snapshot() != rng_before
    assert result.public.score > 0
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.played_pile == []

    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.public.discard_pile == []
    assert run.rng_snapshot() == rng_before


def test_env_r4_hook_play_applies_forced_discards_on_blind_clearing_hand_without_redraw():
    run = _hook_play_run(seed="R4-HOOK-CLEAR", requirement=1)
    selected = [_card_signature(run.public.hand[0])]
    forced, expected_rng = _expected_hook_press_play(run, (0,))

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score >= result.public.blind.requirement
    assert result.public.phase == "ROUND_EVAL"
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == 5
    assert [_card_signature(card) for card in result.public.discard_pile] == forced + selected
    assert result.rng_snapshot() == expected_rng
    assert result.played_pile == []


def test_env_r4_hook_play_applies_forced_discards_on_final_hand_loss_without_redraw():
    run = _hook_play_run(
        seed="R4-HOOK-LOSS",
        requirement=9999,
        hands_remaining=1,
    )
    selected = [_card_signature(run.public.hand[0])]
    forced, expected_rng = _expected_hook_press_play(run, (0,))

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score < result.public.blind.requirement
    assert result.public.phase == "GAME_OVER"
    assert result.public.hands_remaining == 0
    assert len(result.public.hand) == 5
    assert [_card_signature(card) for card in result.public.discard_pile] == forced + selected
    assert result.rng_snapshot() == expected_rng
    assert result.played_pile == []


class _HookPlayDecisionEngine:
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


def test_env_r4_decision_engine_bridge_executes_exact_hook_play():
    run = _hook_play_run(seed="R4-HOOK-BRIDGE")
    selected_indices = (0, 1)
    forced, expected_rng = _expected_hook_press_play(run, selected_indices)
    decision_engine = _HookPlayDecisionEngine()

    result = apply_planned_tactical_step(run, decision_engine)

    assert result.public.score > 0
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert [_card_signature(card) for card in result.public.discard_pile[:2]] == forced
    assert result.rng_snapshot() == expected_rng
    assert decision_engine.observation is not run.public
    assert decision_engine.observation.boss_name == "The Hook"
