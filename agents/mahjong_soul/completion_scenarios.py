"""Offline bounded ready-hand repairs and explicit Ron sensitivity scenarios.

Scenario probabilities describe this replacement-pool model, not real win odds.
A missed unchanged-hand draw conservatively disables all future Ron, since its
untracked Tsumogiri could otherwise create Furiten. No live policy imports this.
"""
from copy import deepcopy
from functools import lru_cache
from math import isfinite
from agents.mahjong_soul.attack_value import own_player, tenpai_value
from agents.mahjong_soul.efficiency import KINDS, counts34, shanten, tile_supply
from games.mahjong_soul.live.runtime.kan import tile_kind


class StateBudgetExceeded(Exception):
    pass


def estimate_completion(board, *, horizon=12, ready_repairs=1, ron_rate=0.0, max_states=5000):
    """Own-turn cycle cost with at most one equal-Shanten repair at Tenpai.

    Ron scenarios assume each opponent independently exposes a uniform public
    unknown tile with probability ron_rate per cycle. This is an input assumption,
    never an inferred opponent discard probability. No new Riichi is assumed.
    Non-ready equal-Shanten changes and future calls are outside this model.
    """
    if type(horizon) is not int or not 1 <= horizon <= 30:
        raise ValueError('Horizon must be between 1 and 30')
    if type(ready_repairs) is not int or ready_repairs not in (0, 1):
        raise ValueError('Ready repair budget must be zero or one')
    if type(ron_rate) not in (int, float) or not isfinite(ron_rate) or not 0 <= ron_rate <= 1:
        raise ValueError('Ron rate must be a finite number between zero and one')
    if type(max_states) is not int or max_states < 1:
        raise ValueError('State budget must be positive')
    if not board.get('visibility_complete') or board['player_count'] not in (3, 4):
        raise ValueError('Complete visibility and supported player count required')
    own = own_player(board)
    fixed = len(own['melds'])
    counts = counts34(board['self']['hand'])
    if sum(counts) != 13 - 3*fixed:
        raise ValueError('Expected draw-stage hand')
    visible = counts34([t for t,n in board['visible_tile_counts'].items() for _ in range(n)])
    supply = tuple(tile_supply(board,t) for t in KINDS)
    own_counts = counts34(board['self']['hand'] + [t for m in own['melds'] for t in m['tiles']])
    if any(visible[i] < own_counts[i] or visible[i] > supply[i] for i in range(34)):
        raise ValueError('Visibility omits own tiles or exceeds supply')
    pool = tuple(supply[i]-visible[i] for i in range(34))
    distance = shanten(counts, fixed)
    metadata = {'model': 'bounded_ready_repair_ron_sensitivity', 'horizon': horizon,
                'ready_repair_budget': ready_repairs, 'ron_rate_assumption': ron_rate,
                'ron_opponents': board['player_count']-1, 'riichi_assumed': False,
                'nonready_equal_shanten_changes': False, 'future_calls': False,
                'furiten_after_untracked_discard': 'conservatively_block_all_future_ron',
                'live_eligible': False}
    if distance not in (0, 1, 2):
        return {**metadata, 'available': False, 'reason': 'unsupported_shanten', 'shanten': distance}
    base = deepcopy(board)
    base['self']['scoring_context'] = {}
    original_river = frozenset(KINDS.index(tile_kind(d['tile'])) for d in own['discards'])
    locked = own.get('riichi') in ('declared', 'accepted')
    visited = 0; repairs_considered = 0

    @lru_cache(maxsize=None)
    def legal_waits(state):
        trial = deepcopy(base)
        # Legality depends on retained tiles and fixed scoring context. Public
        # availability and Furiten are applied separately for each search state.
        own_player(trial)['discards'] = []
        trial['self']['furiten'] = False
        tiles = [t for i,t in enumerate(KINDS) for _ in range(state[i])]
        fixed_tiles = [t for m in own['melds'] for t in m['tiles']]
        for suit in 'mps':
            normal = '5'+suit; red = '0'+suit
            if red not in fixed_tiles and tiles.count(normal)+fixed_tiles.count(normal) > 3:
                tiles[tiles.index(normal)] = red
        result = tenpai_value(trial, tiles)
        tsumo = frozenset(KINDS.index(w['tile']) for w in result['waits'] if 'tsumo' in w['values'])
        ron = frozenset(KINDS.index(w['tile']) for w in result['waits'] if 'dama' in w['values'])
        structural = frozenset(KINDS.index(w['tile']) for w in result['waits'])
        return tsumo, ron, structural

    def profile(state, remaining, river):
        tsumo, ron, structural = legal_waits(state)
        if base['self'].get('furiten') is True or structural & river:
            ron = frozenset()
        return tsumo, ron

    @lru_cache(maxsize=None)
    def solve(state, remaining, river, repairs, ron_blocked):
        nonlocal visited, repairs_considered
        visited += 1
        if visited > max_states:
            raise StateBudgetExceeded
        level = shanten(state, fixed); total = sum(remaining)
        tsumo, ron = profile(state, remaining, river) if level == 0 else (frozenset(), frozenset())
        ron_copies = 0 if ron_blocked else sum(remaining[i] for i in ron)
        ron_chance = 1-(1-ron_rate*ron_copies/total)**(board['player_count']-1) if total else 0
        own_win = sum(remaining[i] for i in tsumo)/total if total else 0
        branches = []
        for draw,copies in enumerate(remaining):
            if not copies or state[draw] == 4 or draw in tsumo:
                continue
            tiles = list(state); tiles[draw] += 1
            next_pool = list(remaining); next_pool[draw] -= 1
            next_pool = tuple(next_pool)
            children = []
            if level > 0:
                if shanten(tuple(tiles), fixed) >= level:
                    continue
                for discard,n in enumerate(tiles):
                    if not n: continue
                    tiles[discard] -= 1
                    if shanten(tuple(tiles), fixed) == level-1:
                        next_river = river | frozenset((discard,))
                        children.append(solve(tuple(tiles),next_pool,next_river,repairs,ron_blocked))
                    tiles[discard] += 1
            elif repairs and not locked:
                for discard,n in enumerate(tiles):
                    if not n or discard == draw: continue
                    tiles[discard] -= 1
                    after = tuple(tiles)
                    if shanten(after,fixed) == 0:
                        next_river = river | frozenset((discard,))
                        next_tsumo,next_ron = profile(after,next_pool,next_river)
                        # Strictly more one-cycle legal completion chance is a
                        # bounded shortlist, not an exhaustive search of repairs.
                        next_r = 0 if ron_blocked else sum(next_pool[i] for i in next_ron)
                        next_n = sum(next_pool)
                        next_chance = 1-(1-sum(next_pool[i] for i in next_tsumo)/next_n)*(
                            1-ron_rate*next_r/next_n)**(board['player_count']-1) if next_n else 0
                        current_chance = ron_chance+(1-ron_chance)*own_win
                        if next_chance > current_chance + 1e-12:
                            repairs_considered += 1
                            children.append(solve(after,next_pool,next_river,repairs-1,ron_blocked))
                    tiles[discard] += 1
            if children:
                branches.append((copies/total, children))
        branch_probability = sum(weight for weight,_ in branches)
        failure_probability = max(0.0,1-own_win-branch_probability)
        # We did not track the exact unchanged-hand discard on failure. Disable
        # subsequent Ron rather than silently assuming it cannot cause Furiten.
        fallback = solve(state,remaining,river,repairs,True) if ron_rate and not ron_blocked and failure_probability else None
        costs = [0.0]; probabilities = [0.0]
        for turns in range(1,horizon+1):
            stay_cost = fallback[0][turns-1] if fallback else costs[-1]
            stay_probability = fallback[1][turns-1] if fallback else probabilities[-1]
            continuation_cost = failure_probability*stay_cost
            continuation_probability = own_win+failure_probability*stay_probability
            for weight,children in branches:
                # Keeping the original hand remains legal; a repair is optional.
                choices = children
                best = min(choices, key=lambda c:(round(c[0][turns-1],12),-c[1][turns-1]))
                if level == 0 and (round(stay_cost,12),-stay_probability) < (round(best[0][turns-1],12),-best[1][turns-1]):
                    continuation_cost += weight*stay_cost
                    continuation_probability += weight*stay_probability
                else:
                    continuation_cost += weight*best[0][turns-1]
                    continuation_probability += weight*best[1][turns-1]
            costs.append(1+(1-ron_chance)*continuation_cost)
            probabilities.append(ron_chance+(1-ron_chance)*continuation_probability)
        return tuple(costs),tuple(probabilities)

    try:
        costs, probabilities = solve(counts,pool,original_river,ready_repairs,False)
    except StateBudgetExceeded:
        return {**metadata,'available':False,'reason':'state_budget','states':visited}
    return {**metadata,'available':True,'shanten':distance,'states':visited,
            'repair_branches':repairs_considered,'capped_cycle_cost':costs[-1],
            'scenario_completion_probability':probabilities[-1]}
