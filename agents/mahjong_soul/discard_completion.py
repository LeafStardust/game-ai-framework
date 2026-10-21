"""Bounded legal-completion ranking for Three-Player East discards."""
from copy import deepcopy
from agents.mahjong_soul.attack_value import own_player
from agents.mahjong_soul.attack_defense import threats
from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
from games.mahjong_soul.live.runtime.kan import tile_kind
from agents.mahjong_soul.efficiency import counts34, KINDS, tile_supply, INDEX
from agents.mahjong_soul.speed_lookahead import development_quality


def choose_completion_discard(board, options, key, *, estimator=estimate_tsumo_draws):
    """Preserve nearest Shanten; compare baseline plus two distinct alternatives.

    Development potential selects two alternatives; immediate copies can be
    traded only when the bounded completion cost favors that path. A failed forecast for
    any shortlisted option preserves the baseline rather than biasing selection.
    Three-Player East v0.7 enables this branch; other playbooks leave it off.
    """
    baseline=max(options,key=key);own=own_player(board)
    if (board['player_count']!=3 or baseline['shanten']!=2 or own['melds']
            or own.get('riichi') in ('declared','accepted') or threats(board)):
        return baseline
    wall=board.get('wall_remaining')
    horizon=min(12,max(1,wall//3)) if type(wall) is int else 12
    if horizon<3:return baseline
    groups={}
    counts=counts34(board['self']['hand'])
    visible=counts34([t for t,n in board['visible_tile_counts'].items() for _ in range(n)])
    unseen=tuple(tile_supply(board,t)-visible[i] for i,t in enumerate(KINDS))
    for option in sorted(options,key=key,reverse=True):
        if option['shanten']==2 and option['effective_ukeire']>0:
            after=list(counts);after[INDEX[tile_kind(option['action']['tile'])]]-=1
            # Closed Tsumo legality is invariant to a permutation of honors.
            # Equal (retained count, unseen copies) honor profiles therefore
            # describe the same forecast, even when their discard labels differ.
            # Keep the strongest original safety/value representative.
            signature=(tuple(after[:27]),tuple(sorted((after[i],unseen[i]) for i in range(27,34))))
            groups.setdefault(signature,option)
    alternatives=[o for o in groups.values() if o is not baseline]
    for option in alternatives:option['completion_development_proxy']=development_quality(board,option)
    shortlist=[baseline]+sorted(alternatives,key=lambda o:(o['completion_development_proxy'],*key(o)),reverse=True)[:2]
    if len(shortlist)<2:return baseline
    for option in shortlist:
        after=deepcopy(board);discard=option['action']['tile']
        after['self']['hand'].remove(discard)
        own_player(after)['discards'].append({'tile':discard})
        result=estimator(after,horizon=horizon,max_states=2000)
        option['completion_estimate']=result
    if not all(o['completion_estimate']['available'] for o in shortlist):return baseline
    # Completion cost is primary; equal numerical costs preserve the established
    # immediate-speed/defense/value ordering rather than inventing new tie rules.
    chosen=max(shortlist,key=lambda o:(-round(o['completion_estimate']['capped_draw_cost'],12),*key(o)))
    chosen['completion_baseline_action']=deepcopy(baseline['action'])
    return chosen
