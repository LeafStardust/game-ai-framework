"""Experimental Sanma East call guard; enabled only by the offline simulator."""
from copy import deepcopy
from agents.mahjong_soul.attack_value import own_player
from agents.mahjong_soul.completion_scenarios import estimate_completion
from agents.mahjong_soul.efficiency import counts34,shanten


def guard_opening(board, candidates, diagnostics=None, *, estimator=estimate_completion):
    """Skip a selected unsecured opening only if both bounded costs support it.

    Candidates arrive in the existing policy's preference order. Unsupported
    forecasts preserve the original action. No live factory enables this guard.
    """
    own=own_player(board)
    if (board['player_count']!=3 or any(m['type']!=3 for m in own['melds'])
            or shanten(counts34(board['self']['hand']),len(own['melds']))!=2):
        return candidates[0] if candidates else None
    before=None
    for action,option in candidates:
        if option['shanten']!=1 or option['open_yaku'] or action['kind']!='pon':return action,option
        if before is None:before=estimator(board,ready_repairs=1,ron_rate=0.0,horizon=12,max_states=5000)
        post=deepcopy(board)
        for tile in action['combination'].split('|'):post['self']['hand'].remove(tile)
        discard=option['action']['tile'];post['self']['hand'].remove(discard)
        player=own_player(post)
        player['melds'].append({'type':1,'tiles':action['combination'].split('|')+[action['called_tile']]})
        player['discards'].append({'tile':discard})
        after=estimator(post,ready_repairs=1,ron_rate=0.0,horizon=12,max_states=5000) if before['available'] else {'available':False,'reason':'baseline_unavailable'}
        reject=(before['available'] and after['available']
                and before['capped_cycle_cost'] < after['capped_cycle_cost']-1e-10)
        if diagnostics is not None:
            for note in diagnostics:
                if note['action']==action:
                    note['completion_guard']={'skip':before,'call':after,'rejected':reject}
                    if reject:
                        note['accepted']=False
                        note['rejections']['slower_legal_completion']=1
                    break
        if not reject:return action,option
    return None
