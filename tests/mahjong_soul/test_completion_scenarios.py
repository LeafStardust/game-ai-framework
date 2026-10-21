"""Exact legality and explicit assumptions in offline completion scenarios."""
from collections import Counter
from copy import deepcopy
import pytest
from agents.mahjong_soul.completion_scenarios import estimate_completion
from agents.mahjong_soul.attack_value import own_player
from tests.mahjong_soul.test_completion_speed import ready_board


def repairable_board():
    board = ready_board()
    board['self']['hand'] = ['2p','3p','4p','3p','4p','5p','6s','7s','8s','1z']
    own = own_player(board)
    own['melds'] = [{'type':1,'tiles':['3s']*3}]
    own['discards'] = []
    board['visible_tile_counts'] = dict(Counter(board['self']['hand']+['3s']*3))
    return board


def test_no_yaku_ready_hand_can_be_repaired_without_losing_tenpai():
    board = repairable_board(); original = deepcopy(board)
    blocked = estimate_completion(board,ready_repairs=0,horizon=4)
    repaired = estimate_completion(board,ready_repairs=1,horizon=4)
    assert blocked['scenario_completion_probability'] == 0
    assert blocked['capped_cycle_cost'] == 4
    assert repaired['repair_branches'] > 0
    assert repaired['scenario_completion_probability'] > 0
    assert repaired['capped_cycle_cost'] < 4
    assert board == original


def test_explicit_one_cycle_ron_assumption_has_analytic_probability():
    board = ready_board(True); own_player(board)['discards'] = []
    board['self']['furiten'] = False
    result = estimate_completion(board,horizon=1,ready_repairs=0,ron_rate=.5)
    unseen = 136-sum(board['visible_tile_counts'].values())
    self_chance = 3/unseen
    ron_chance = 1-(1-.5*3/unseen)**3
    expected = ron_chance+(1-ron_chance)*self_chance
    assert result['scenario_completion_probability'] == pytest.approx(expected)
    assert result['capped_cycle_cost'] == 1
    assert result['live_eligible'] is False


def test_actual_furiten_blocks_ron_but_preserves_tsumo():
    board = ready_board(True); board['self']['furiten'] = True
    no_ron = estimate_completion(board,ready_repairs=0,ron_rate=0,horizon=3)
    scenario = estimate_completion(board,ready_repairs=0,ron_rate=1,horizon=3)
    assert scenario['scenario_completion_probability'] == pytest.approx(no_ron['scenario_completion_probability'])
    assert scenario['scenario_completion_probability'] > 0


def test_exhausted_structural_river_wait_still_blocks_other_live_ron_wait():
    board = ready_board(True); own = own_player(board)
    board['self']['hand'] = ['1m']*3+['4p','5p','6p','6s','7s','1z','1z']
    own['discards'] = [{'tile':'5s'}]*4
    board['visible_tile_counts'] = dict(Counter(board['self']['hand']+['5z']*3+['5s']*4))
    no_ron = estimate_completion(board,ready_repairs=0,ron_rate=0,horizon=3)
    scenario = estimate_completion(board,ready_repairs=0,ron_rate=1,horizon=3)
    assert scenario['scenario_completion_probability'] == pytest.approx(no_ron['scenario_completion_probability'])
    assert scenario['scenario_completion_probability'] > 0


def test_accepted_riichi_cannot_change_the_hand():
    board = repairable_board(); own_player(board)['riichi'] = 'accepted'
    result = estimate_completion(board,ready_repairs=1,horizon=3)
    assert result['repair_branches'] == 0


def test_budget_is_explicit_not_a_partial_favorable_estimate():
    result = estimate_completion(repairable_board(),max_states=1)
    assert result['available'] is False and result['reason'] == 'state_budget'
    assert 'scenario_completion_probability' not in result


@pytest.mark.parametrize('kwargs',[{'ron_rate':float('nan')},{'ron_rate':-1},{'ron_rate':True},
                                   {'ready_repairs':2},{'horizon':0},{'max_states':0}])
def test_invalid_settings_rejected(kwargs):
    with pytest.raises(ValueError):estimate_completion(ready_board(True),**kwargs)


def test_untracked_missed_draw_conservatively_disables_future_ron():
    board = ready_board(True); own_player(board)['discards'] = []
    board['self']['furiten'] = False
    n = 136-sum(board['visible_tile_counts'].values())
    t = 3/n; r = 1-(1-3/n)**3
    first = r+(1-r)*t
    expected = first+(1-r)*(1-t)*t
    result = estimate_completion(board,horizon=2,ready_repairs=0,ron_rate=1)
    assert result['scenario_completion_probability'] == pytest.approx(expected)


def test_planned_repair_discard_blocks_a_future_ron_wait(monkeypatch):
    from agents.mahjong_soul import completion_scenarios as model
    # Isolate a hypothetical route that gains Ron only by discarding its own
    # eventual waiting tile. That discard must invalidate the apparent gain.
    def waits(board, hand):
        return {'waits': [{'tile':'1z','values':{'dama':{}}}] if '1z' not in hand else []}
    monkeypatch.setattr(model,'tenpai_value',waits)
    result = estimate_completion(repairable_board(),horizon=3,ron_rate=1)
    assert result['scenario_completion_probability'] == 0
    assert result['repair_branches'] == 0


def test_zero_repairs_zero_ron_preserves_previous_optimal_tsumo_cost():
    import json
    from pathlib import Path
    from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
    req = json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]['request']
    board = req['observation']['board']
    old = estimate_tsumo_draws(board)
    new = estimate_completion(board,ready_repairs=0,ron_rate=0)
    assert new['capped_cycle_cost'] == pytest.approx(old['capped_draw_cost'])
    # Roundoff-equivalent cost ties now consistently prefer more completion.
    assert new['scenario_completion_probability'] >= old['completion_probability'] - 1e-12
