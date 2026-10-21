"""Compare one selected Pon with legal Skip in a seeded offline match."""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
from agents.mahjong_soul.simulation import Agent,run,OPPONENT_PROFILES,ENGINE_VERSION,KINDS


def compare_call(seed,seat,called_tile,*,opponents='callers',occurrence=1,mode='3p-red-east'):
    if occurrence<1:raise ValueError('Occurrence must be positive')
    target={};seen=0;overrides=0
    def baseline_factory(name):
        agent=Agent(name)
        if agent.policy:
            choose=agent.policy.choose
            def traced(request):
                nonlocal seen
                action=choose(request)
                if (request['observation']['board']['self_seat']==seat and
                        action['kind']=='pon' and action.get('called_tile')==called_tile):
                    seen+=1
                    if seen==occurrence:
                        target.update(request=deepcopy(request),action=deepcopy(action),
                                      analysis=deepcopy(agent.policy.last_analysis),
                                      hand_index=sum(e['type']=='start_kyoku' for e in agent.history)-1)
                return action
            agent.policy.choose=traced
        return agent
    baseline=run(seed,seat,'east_speed',opponents=opponents,mode=mode,agent_factory=baseline_factory)
    if not target:raise ValueError('Requested selected Pon was not encountered')
    def skip_factory(name):
        agent=Agent(name)
        if agent.policy:
            choose=agent.policy.choose
            def filtered(request):
                nonlocal overrides
                if (request['observation']['board']['self_seat']==seat and
                        request['board_token']==target['request']['board_token']):
                    if overrides:raise ValueError('Counterfactual target repeated')
                    if any(a['kind'] in ('discard','riichi','ron','tsumo') for a in request['actions']):
                        raise ValueError('Target must be a pure call response')
                    skip=next((a for a in request['actions'] if a['kind']=='skip'),None)
                    if skip is None or target['action'] not in request['actions']:
                        raise ValueError('Target Pon or legal Skip missing')
                    overrides+=1
                    # Route the real policy through Skip before it remembers
                    # any hypothetical post-Pon plan. Native binding still
                    # comes from the original engine-legal action list.
                    modified=dict(request,actions=[deepcopy(skip)])
                    action=choose(modified)
                    if action!=skip:raise ValueError('Policy did not select the forced legal Skip')
                    return action
                return choose(request)
            agent.policy.choose=filtered
        return agent
    skipped=run(seed,seat,'east_speed',opponents=opponents,mode=mode,agent_factory=skip_factory)
    if overrides!=1:raise ValueError('Counterfactual did not reach exactly one matching target')
    if baseline['initial_deal_digest']!=skipped['initial_deal_digest']:
        raise ValueError('Starting deals differ')
    first=next((i for i,(a,b) in enumerate(zip(baseline['log'],skipped['log'])) if a!=b),None)
    if first is None:raise ValueError('Selected Pon and Skip produced no observable divergence')
    event=baseline['log'][first]
    if event.get('type')!='pon' or event.get('actor')!=seat:
        raise ValueError('Replays diverged before the targeted Pon')
    def hand_summary(result):
        index=-1;events=[]
        for event in result['log']:
            if event['type']=='start_kyoku':index+=1
            if index==target['hand_index']:events.append(event)
        return {'hand_index':target['hand_index'],
                'wins':sum(e['type']=='hora' and e.get('actor')==seat for e in events),
                'deal_in':any(e['type']=='hora' and e.get('target')==seat and e.get('actor')!=seat for e in events),
                'settlements':[e for e in events if e['type'] in ('hora','ryukyoku')],
                'own_discards':sum(e['type']=='dahai' and e.get('actor')==seat for e in events)}
    report={'mode':'offline_single_call_counterfactual','seed':seed,'seat':seat,'called_tile':called_tile,
            'occurrence':occurrence,'opponents':opponents,'engine':ENGINE_VERSION,
            'target':target,'overrides':overrides,'first_different_event_index':first,
            'first_different_events':{'pon':baseline['log'][first],'skip':skipped['log'][first]},
            'branches':{name:{'metrics':{k:v for k,v in result.items() if k!='log'},'target_hand':hand_summary(result)}
                        for name,result in [('pon',baseline),('skip',skipped)]},
            'limitation':'One forced action on one fixed hidden deal; later draws diverge. This is not a win-rate estimate or an optimal-action proof.'}
    return report,baseline['log'],skipped['log']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,required=True);parser.add_argument('--seat',type=int,choices=range(3),required=True)
    parser.add_argument('--called-tile',choices=KINDS+['0m','0p','0s'],required=True);parser.add_argument('--occurrence',type=int,default=1)
    parser.add_argument('--opponents',choices=list(OPPONENT_PROFILES),default='callers')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.seed<0 or args.occurrence<1:parser.error('Seed must be nonnegative and occurrence positive')
    if importlib.metadata.version('riichienv')!=ENGINE_VERSION:parser.error('Install the pinned simulator requirements')
    if args.output.exists():parser.error('Output already exists; choose a new directory')
    report,pon,skip=compare_call(args.seed,args.seat,args.called_tile,opponents=args.opponents,occurrence=args.occurrence)
    root=Path(__file__).resolve().parents[2]
    report['revision']=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    report['source_hashes']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted([*(root/'agents/mahjong_soul').glob('*.py'),*(root/'games/mahjong_soul/playbook').rglob('*.py')])}
    args.output.mkdir(parents=True)
    for name,events in [('pon',pon),('skip',skip)]:
        (args.output/f'{name}.json').write_text(json.dumps({'events':events},indent=2),encoding='utf-8')
    (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('target','source_hashes')},indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
