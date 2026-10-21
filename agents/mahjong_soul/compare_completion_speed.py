"""Measure structural Tenpai speed on saved public Pon requests, offline only."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
from agents.mahjong_soul.completion_speed import estimate_tenpai_draws, estimate_tsumo_draws
from agents.mahjong_soul.efficiency import KINDS, counts34, tile_supply
from agents.mahjong_soul.policy import make_policy


def compare_request(request, *, horizon=12):
    original = deepcopy(request)
    board = request['observation']['board']
    own = next(p for p in board['players'] if p['seat'] == board['self_seat'])
    if not board.get('visibility_complete'):
        raise ValueError('Incomplete public visibility')
    visible = counts34([t for t, n in board['visible_tile_counts'].items() for _ in range(n)])
    unseen = [tile_supply(board, tile) - visible[i] for i, tile in enumerate(KINDS)]
    policy = make_policy('playbook', 'atk')
    action = policy.choose(request)
    if action['kind'] != 'pon':
        raise ValueError('Expected a selected Pon')
    discard = policy.last_analysis['post_call_discard']['tile']
    before = list(board['self']['hand']); after = list(before)
    for tile in action['combination'].split('|'):
        after.remove(tile)
    after.remove(discard)
    # Called tile was already visible in the opponent river. Moving tiles to a
    # meld/discard changes no public availability and introduces no future data.
    start = perf_counter()
    skip = estimate_tenpai_draws(before, unseen, meld_count=len(own['melds']), horizon=horizon)
    pon = estimate_tenpai_draws(after, unseen, meld_count=len(own['melds'])+1, horizon=horizon)
    post_board = deepcopy(board)
    post_board['self']['hand'] = after
    post_own = next(p for p in post_board['players'] if p['seat'] == board['self_seat'])
    post_own['melds'].append({'type': 1, 'tiles': action['combination'].split('|') + [action['called_tile']]})
    tsumo_skip = estimate_tsumo_draws(board, horizon=horizon)
    tsumo_pon = estimate_tsumo_draws(post_board, horizon=horizon)
    assert request == original
    return {'board_token': request['board_token'], 'action': action,
            'post_call_discard': discard, 'skip': skip, 'pon': pon,
            'tsumo_skip': tsumo_skip, 'tsumo_pon': tsumo_pon,
            'seconds': perf_counter()-start,
            'live_eligible': False, 'reason': 'own_draw_model_excludes_calls_ron_and_equal_shanten_repairs'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requests', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--horizon', type=int, default=12)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output already exists')
    cases = json.loads(args.requests.read_text(encoding='utf-8'))
    results = [compare_request(c['request'], horizon=args.horizon) for c in cases]
    args.output.write_text(json.dumps({'model': 'useful-draw-only structural Tenpai and scored legal Tsumo',
                                      'results': results}, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
