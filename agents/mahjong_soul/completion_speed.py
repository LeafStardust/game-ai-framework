"""Offline finite-horizon structural Tenpai model; never a win probability.

Only useful draws deplete the public pool. Unhelpful draws are returned to it.
Opponents, calls, Yaku, Furiten and shape improvements at equal Shanten are
excluded. The result must not be used as a legal-win or live call evaluator.
"""
from functools import lru_cache
from agents.mahjong_soul.efficiency import counts34, shanten, KINDS


def estimate_tenpai_draws(hand, unseen, *, meld_count=0, horizon=12, max_states=20000, _ready_copies=None):
    """Return E[min(draws to structural Tenpai, horizon)] and reach probability.

    After a useful draw, choose the discard minimizing remaining capped draw
    cost. A blocked branch costs the entire remaining horizon, rather than
    disappearing from an average. Availability includes unknown opponent tiles;
    it is not the actual live-wall distribution. Supports at most two Shanten.
    """
    counts = counts34(hand)
    pool = tuple(unseen)
    if len(pool) != 34 or any(type(n) is not int or n < 0 or n > 4 for n in pool):
        raise ValueError('Expected 34 public unseen copy counts')
    if any(counts[i] + pool[i] > 4 for i in range(34)):
        raise ValueError('Hand and unseen copies exceed tile supply')
    if type(horizon) is not int or not 1 <= horizon <= 30:
        raise ValueError('Horizon must be between 1 and 30')
    if type(max_states) is not int or max_states < 1:
        raise ValueError('State budget must be positive')
    if sum(counts) != 13 - 3 * meld_count:
        raise ValueError('Expected a draw-stage concealed hand')
    distance = shanten(counts, meld_count)
    if distance not in (0, 1, 2):
        return {'available': False, 'reason': 'unsupported_shanten', 'shanten': distance}
    visited = 0

    @lru_cache(maxsize=None)
    def solve(state, remaining):
        nonlocal visited
        visited += 1
        if visited > max_states:
            raise OverflowError
        level = shanten(state, meld_count)
        if level == 0:
            if _ready_copies is None:
                return (0.0,) * (horizon + 1), (1.0,) * (horizon + 1)
            copies = _ready_copies(state, remaining)
            total = sum(remaining)
            chance = copies / total if total else 0
            costs = [0.0]; probabilities = [0.0]
            for _ in range(horizon):
                costs.append(1 + (1-chance)*costs[-1])
                probabilities.append(chance + (1-chance)*probabilities[-1])
            return tuple(costs), tuple(probabilities)
        total = sum(remaining)
        branches = []
        for draw, copies in enumerate(remaining):
            if not copies or state[draw] == 4:
                continue
            tiles = list(state); tiles[draw] += 1
            if shanten(tuple(tiles), meld_count) >= level:
                continue
            next_pool = list(remaining); next_pool[draw] -= 1
            children = []
            for discard, count in enumerate(tiles):
                if not count:
                    continue
                tiles[discard] -= 1
                if shanten(tuple(tiles), meld_count) == level - 1:
                    children.append(solve(tuple(tiles), tuple(next_pool)))
                tiles[discard] += 1
            if children:
                branches.append((copies / total, children))
        useful_probability = sum(p for p, _ in branches)
        costs = [0.0]; probabilities = [0.0]
        for turns in range(1, horizon + 1):
            cost = 1 + (1 - useful_probability) * costs[-1]
            probability = (1 - useful_probability) * probabilities[-1]
            for weight, children in branches:
                child = min(children, key=lambda c: (c[0][turns-1], -c[1][turns-1]))
                cost += weight * child[0][turns-1]
                probability += weight * child[1][turns-1]
            costs.append(cost); probabilities.append(probability)
        return tuple(costs), tuple(probabilities)

    try:
        costs, probabilities = solve(counts, pool)
    except OverflowError:
        return {'available': False, 'reason': 'state_budget', 'states': visited}
    return {'available': True, 'target': 'legal_tsumo' if _ready_copies else 'structural_tenpai', 'shanten': distance,
            'horizon': horizon, 'capped_draw_cost': costs[-1],
            ('completion_probability' if _ready_copies else 'tenpai_probability'): probabilities[-1], 'states': visited,
            'legal_win_evaluated': _ready_copies is not None}


def estimate_tsumo_draws(board, *, horizon=12, max_states=20000, minimum_han=0):
    """Offline own-draw-only legal completion, with exact scored ready waits.

    No hypothetical Riichi or situational Yaku are granted. Furiten cannot
    prohibit Tsumo. Equal-Shanten repairs and calls remain excluded, including
    repair of no-Yaku Tenpai; these branches remain blocked in this model.
    The optional South Han floor counts only scored waits meeting that floor.
    Without it, canonical normal fives preserve the original legality-only model.
    """
    from copy import deepcopy
    from agents.mahjong_soul.attack_value import tenpai_value, own_player
    from agents.mahjong_soul.efficiency import tile_supply
    if not board.get('visibility_complete'):
        raise ValueError('Incomplete public visibility')
    own = own_player(board)
    visible = counts34([t for t, n in board['visible_tile_counts'].items() for _ in range(n)])
    supply = tuple(tile_supply(board, t) for t in KINDS)
    unseen = tuple(supply[i] - visible[i] for i in range(34))
    base = deepcopy(board)
    # These context-dependent bonuses cannot be assumed on hypothetical draws.
    base['self']['scoring_context'] = {}

    def ready_copies(state, remaining):
        trial = deepcopy(base)
        trial['visible_tile_counts'] = {t: supply[i]-remaining[i] for i,t in enumerate(KINDS)}
        tiles = [t for i,t in enumerate(KINDS) for _ in range(state[i])]
        # The exact scorer reserves a physical copy for each red five. A
        # hypothetical hand holding all four fives cannot encode all as normal.
        for suit in 'mps':
            normal = '5' + suit; red = '0' + suit
            fixed = [t for m in own['melds'] for t in m['tiles']]
            known_red=minimum_han>0 and red in base['self']['hand'] and normal in tiles
            if red not in fixed and (known_red or tiles.count(normal) + fixed.count(normal) > 3):
                tiles[tiles.index(normal)] = red
        profile = tenpai_value(trial, tiles)
        if not profile:return 0
        if minimum_han:
            return sum(w['unseen'] for w in profile['waits']
                       if w.get('values',{}).get('tsumo',{}).get('legal')
                       and w['values']['tsumo']['han']>=minimum_han)
        return profile['tsumo_ukeire']

    result = estimate_tenpai_draws(board['self']['hand'], unseen,
                                  meld_count=len(own['melds']), horizon=horizon,
                                  max_states=max_states, _ready_copies=ready_copies)
    if minimum_han:result['minimum_han']=minimum_han
    result['ron_evaluated'] = False
    result['riichi_assumed'] = False
    result['equal_shanten_repairs'] = False
    return result
