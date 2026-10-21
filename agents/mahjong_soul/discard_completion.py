"""Bounded completion ranking with separate East and South objectives."""
import math
from copy import deepcopy
from agents.mahjong_soul.attack_value import own_player
from agents.mahjong_soul.attack_defense import threats
from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
from games.mahjong_soul.live.runtime.kan import tile_kind
from agents.mahjong_soul.efficiency import counts34, KINDS, tile_supply, INDEX
from agents.mahjong_soul.speed_lookahead import development_quality


def choose_completion_discard(board, options, key, *, estimator=estimate_tsumo_draws, allow_yonma=False, honor_equivalence=True):
    """Preserve nearest Shanten; compare baseline plus two distinct alternatives.

    Development potential selects two alternatives; immediate copies can be
    traded only when the bounded completion cost favors that path. A failed forecast for
    any shortlisted option preserves the baseline rather than biasing selection.
    East enables direct speed ranking; South calls through its value guard.
    """
    baseline=max(options,key=key);own=own_player(board)
    if (board['player_count'] not in ((3,4) if allow_yonma else (3,)) or baseline['shanten']!=2 or own['melds']
            or own.get('riichi') in ('declared','accepted') or threats(board)):
        return baseline
    wall=board.get('wall_remaining')
    horizon=min(12,max(1,wall//board['player_count'])) if type(wall) is int else 12
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
            signature=(tuple(after[:27]),tuple(sorted((after[i],unseen[i]) for i in range(27,34)))) if honor_equivalence else tuple(after)
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


def choose_attack_completion_discard(board, options, key, *, estimator=estimate_tsumo_draws):
    """Compare completion only within the baseline's protected attack route.

    The caller already enforces nearest scoring distance and its copy floor.
    Preserve target Han, route, Dora and pair structure before forecasting.
    Qualified Yakuman plans retain their specialized feasibility model.
    """
    baseline=max(options,key=key)
    if str(baseline.get("target_route","")).startswith("yakuman_"):return baseline
    protected=("projected_han","target_route","target_suit","yakuman_suit")
    eligible=[o for o in options if all(o.get(k)==baseline.get(k) for k in protected)
              and o.get("route_cost",0)<=baseline.get("route_cost",0)
              and o.get("dora_loss",0)<=baseline.get("dora_loss",0)
              and o.get("pair_break_loss",0)<=baseline.get("pair_break_loss",0)]
    def value_estimator(after,**kwargs):
        return estimator(after,minimum_han=math.ceil(baseline["projected_han"]),**kwargs)
    chosen=choose_completion_discard(board,eligible,key,estimator=value_estimator,
                                     allow_yonma=True,honor_equivalence=False)
    if "completion_baseline_action" in chosen:
        chosen["completion_objective"]="attack_value_preserving"
    return chosen
