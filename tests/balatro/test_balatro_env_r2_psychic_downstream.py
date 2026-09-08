from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.state import BalatroState


def _psychic_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Psychic"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hands_remaining = 1
    state.discards_remaining = 1
    return HeadlessRunState(public=state, seed="PSYCHIC")


def test_env_r2_psychic_short_play_remains_admissible_but_scores_zero():
    started = start_supported_start_inert_boss(_psychic_run())
    evaluator = LiveHandDecisionEvaluator()
    action = BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:4]))

    assert boss_play_action_is_legal(started.public, action)

    projection = evaluator.project_play(started.public, action)

    assert projection.hand_score == 0
    assert projection.expected_hand_score == 0.0
    assert projection.maximum_hand_score == 0
    assert projection.projected_total == started.public.score
    assert projection.expected_projected_total == float(started.public.score)
    assert projection.maximum_projected_total == started.public.score


def test_env_r2_psychic_five_card_play_uses_normal_scoring_path():
    started = start_supported_start_inert_boss(_psychic_run())
    evaluator = LiveHandDecisionEvaluator()
    action = BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:5]))

    assert boss_play_action_is_legal(started.public, action)

    projection = evaluator.project_play(started.public, action)

    assert projection.hand_score > 0
    assert projection.expected_hand_score > 0.0
    assert projection.maximum_hand_score >= projection.hand_score
    assert projection.projected_total > started.public.score


def test_env_r2_psychic_projection_does_not_mutate_started_state():
    started = start_supported_start_inert_boss(_psychic_run())
    evaluator = LiveHandDecisionEvaluator()
    before_hand = list(started.public.hand)
    before_score = started.public.score
    before_rng = started.rng_snapshot()

    evaluator.project_play(
        started.public,
        BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:4])),
    )

    assert started.public.hand == before_hand
    assert started.public.score == before_score
    assert started.rng_snapshot() == before_rng
