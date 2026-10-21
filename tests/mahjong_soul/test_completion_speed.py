"""Analytic checks for the explicitly limited offline draw-cost model."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul.completion_speed import estimate_tenpai_draws
from agents.mahjong_soul.compare_completion_speed import compare_request
from agents.mahjong_soul.efficiency import KINDS


ONE = ['1m']*3 + ['2p']*3 + ['3s','4s','5s','6s','7s','1z','2z']
READY = ['1m']*3 + ['2p']*3 + ['3s','4s','5s','6s','7s','8s','1z']


def test_ready_is_zero_cost_but_does_not_claim_legal_win():
    result = estimate_tenpai_draws(READY, [0]*34)
    assert result['capped_draw_cost'] == 0
    assert result['tenpai_probability'] == 1
    assert result['legal_win_evaluated'] is False


def test_one_step_geometric_cost_and_probability():
    pool = [0]*34
    pool[KINDS.index('1z')] = 2  # pair makes Tenpai
    pool[KINDS.index('9m')] = 2  # useless draw, returned to pool in this model
    result = estimate_tenpai_draws(ONE, pool, horizon=4)
    assert result['shanten'] == 1
    assert result['capped_draw_cost'] == pytest.approx(1 + .5 + .25 + .125)
    assert result['tenpai_probability'] == pytest.approx(1 - .5**4)


def test_exhausted_progress_is_not_dropped():
    result = estimate_tenpai_draws(ONE, [0]*34, horizon=7)
    assert result['capped_draw_cost'] == 7
    assert result['tenpai_probability'] == 0


def test_successful_draw_is_removed_before_next_stage():
    hand = ['1m']*3 + ['2p']*3 + ['3s','4s','6s','7s','1z','2z','3z']
    pool = [0]*34; pool[KINDS.index('1z')] = 1
    result = estimate_tenpai_draws(hand, pool, horizon=5)
    assert result['shanten'] == 2
    assert result['capped_draw_cost'] == 5
    assert result['tenpai_probability'] == 0


def test_budget_failure_is_explicit():
    pool = [0]*34; pool[KINDS.index('1z')] = 2
    assert estimate_tenpai_draws(ONE, pool, max_states=1)['reason'] == 'state_budget'


@pytest.mark.parametrize('pool', [[0]*33, [-1]*34, [5]*34])
def test_invalid_pool_rejected(pool):
    with pytest.raises(ValueError): estimate_tenpai_draws(ONE, pool)


def test_recorded_call_comparison_does_not_mutate_or_claim_win_speed():
    case = json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]
    before = deepcopy(case)
    result = compare_request(case['request'])
    assert case == before
    assert result['skip']['shanten'] == 2
    assert result['pon']['shanten'] == 1
    assert result['live_eligible'] is False


def ready_board(value_meld=False):
    case = json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]
    board = deepcopy(case['request']['observation']['board'])
    board['player_count'] = 4
    board['self']['hand'] = ['1m']*3 + ['4p','5p','6p','7s','8s','9s','1z']
    own = next(p for p in board['players'] if p['is_self'])
    own['melds'] = [{'type': 1, 'tiles': ['5z' if value_meld else '3p']*3}]
    own['riichi'] = None
    from collections import Counter
    board['visible_tile_counts'] = dict(Counter(board['self']['hand'] + own['melds'][0]['tiles']))
    return board


def test_open_no_yaku_tenpai_is_not_a_legal_completion():
    from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
    result = estimate_tsumo_draws(ready_board(), horizon=6)
    assert result['shanten'] == 0
    assert result['completion_probability'] == 0
    assert result['capped_draw_cost'] == 6
    assert result['legal_win_evaluated'] is True
    assert result['equal_shanten_repairs'] is False


def test_value_yaku_wait_is_legal_and_furiten_does_not_block_tsumo():
    from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
    board = ready_board(True)
    original = deepcopy(board)
    result = estimate_tsumo_draws(board, horizon=6)
    assert 0 < result['completion_probability'] < 1
    board['self']['furiten'] = True
    blocked_ron = estimate_tsumo_draws(board, horizon=6)
    assert blocked_ron['completion_probability'] == result['completion_probability']
    board['self']['furiten'] = original['self']['furiten']
    assert board == original


def test_legal_model_reverses_the_structural_preference_in_recorded_case():
    case = json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]
    result = compare_request(case['request'])
    assert result['pon']['capped_draw_cost'] < result['skip']['capped_draw_cost']
    assert result['tsumo_skip']['capped_draw_cost'] < result['tsumo_pon']['capped_draw_cost']
    assert result['tsumo_skip']['completion_probability'] > result['tsumo_pon']['completion_probability']
    assert result['live_eligible'] is False


def test_hypothetical_four_fives_use_a_physical_red_copy():
    from collections import Counter
    from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
    board = ready_board()
    own = next(p for p in board['players'] if p['is_self'])
    own['melds'] = []
    board['self']['hand'] = ['5p']*4 + ['3p','4p','6s','7s','8s'] + ['1z']*3 + ['2z']
    board['visible_tile_counts'] = dict(Counter(board['self']['hand']))
    result = estimate_tsumo_draws(board)
    assert result['shanten'] == 0
    assert result['completion_probability'] > 0
