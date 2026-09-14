from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.transition import HeadlessRunState
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _arm_run(*, seed="R4-ARM", level=3, requirement=99_999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 9
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Arm"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hand_levels["HIGH_CARD"] = level
    return start_supported_start_inert_boss(
        HeadlessRunState(public=state, seed=seed)
    )


def _high_card_score(card, level):
    chips = 5 + 10 * (level - 1) + BalatroScorer.RANK_CHIPS[card.rank]
    mult = 1 + (level - 1)
    return chips * mult


def test_env_r4_arm_decrements_level_before_scoring_and_preserves_input():
    run = _arm_run(level=3)
    selected = run.public.hand[0]

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.hand_levels["HIGH_CARD"] == 2
    assert result.public.score == _high_card_score(selected, 2)
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert run.public.hand_levels["HIGH_CARD"] == 3
    assert run.public.score == 0


def test_env_r4_arm_level_one_is_noop_and_scores_ordinary_hand():
    run = _arm_run(seed="R4-ARM-ONE", level=1)
    selected = run.public.hand[0]

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.hand_levels["HIGH_CARD"] == 1
    assert result.public.score == _high_card_score(selected, 1)


def test_env_r4_arm_persistent_level_reduction_stops_at_one():
    run = _arm_run(seed="R4-ARM-PERSIST", level=3)

    after_first = apply_supported_ordinary_play(run, (0,))
    after_second = apply_supported_ordinary_play(after_first, (0,))
    result = apply_supported_ordinary_play(after_second, (0,))

    assert after_first.public.hand_levels["HIGH_CARD"] == 2
    assert after_second.public.hand_levels["HIGH_CARD"] == 1
    assert result.public.hand_levels["HIGH_CARD"] == 1
