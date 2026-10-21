"""Full-match action-exposure probe for the offline discard completion policy."""
import argparse
from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
from agents.mahjong_soul.simulation import Agent,run,ENGINE_VERSION
from agents.mahjong_soul.completion_scenario_batch import provenance,save_new


def probe(seed,seat,output,*,opponents='callers'):
    output=Path(output)
    if output.exists():raise ValueError('Output already exists')
    if importlib.metadata.version('riichienv')!=ENGINE_VERSION:raise ValueError('Pinned simulator required')
    examined=[];first=None
    def factory(name):
        agent=Agent(name)
        if name=='east_speed_discard_completion':
            choose=agent.policy.choose
            def traced(request):
                nonlocal first
                action=choose(request);analysis=agent.policy.last_analysis
                notes=[n for n in analysis.get('discard_evaluations',[]) if 'completion_estimate' in n]
                if notes:
                    baseline=analysis.get('completion_baseline_action')
                    changed=action['kind']=='discard' and baseline is not None and action!=baseline
                    examined.append({'board_token':request['board_token'],'action':deepcopy(action),
                                     'baseline_offensive_action':deepcopy(baseline),'changed':changed,'options':deepcopy(notes)})
                    if changed and first is None:
                        first={'request':deepcopy(request),'baseline':deepcopy(baseline),'candidate':deepcopy(action)}
                return action
            agent.policy.choose=traced
        return agent
    source=provenance()
    baseline=run(seed,seat,'east_speed',opponents=opponents)
    candidate=run(seed,seat,'east_speed_discard_completion',opponents=opponents,agent_factory=factory)
    if baseline['initial_deal_digest']!=candidate['initial_deal_digest']:raise ValueError('Paired initial deals differ')
    output.mkdir(parents=True)
    for name,result in [('baseline',baseline),('candidate',candidate)]:
        save_new(output/f'{name}.json',{'metrics':{k:v for k,v in result.items() if k!='log'},'events':result['log']})
    report={**source,'seed':seed,'seat':seat,'opponents':opponents,'engine':ENGINE_VERSION,
            'different_replays':baseline['log']!=candidate['log'],'first_decision_difference':first,
            'forecasted_decisions':len(examined),'changed_discard_decisions':sum(r['changed'] for r in examined),
            'examined':examined,'baseline_metrics':{k:v for k,v in baseline.items() if k!='log'},
            'candidate_metrics':{k:v for k,v in candidate.items() if k!='log'},
            'scope':'Development exposure probe, not independent strength evidence'}
    save_new(output/'report.json',report)
    print(json.dumps({k:report[k] for k in ('seed','seat','different_replays','forecasted_decisions','changed_discard_decisions')}),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,required=True);parser.add_argument('--seat',type=int,choices=[0,1,2],default=0)
    parser.add_argument('--opponents',choices=['callers','aggressive'],default='callers')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    probe(args.seed,args.seat,args.output,opponents=args.opponents)


if __name__=='__main__':main()
