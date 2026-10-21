"""Capture reproducible public call requests and evaluate completion scenarios."""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
from time import perf_counter
from agents.mahjong_soul.attack_value import own_player
from agents.mahjong_soul.completion_scenarios import estimate_completion

SCENARIOS = {'no_repairs': (0,0.0), 'repairs': (1,0.0),
             'repairs_ron_half': (1,0.5), 'repairs_ron_full': (1,1.0)}


def provenance():
    root = Path(__file__).resolve().parents[2]
    return {'revision': subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip(),
            'source_hashes': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted([*(root/'agents/mahjong_soul').glob('*.py'),
                                              *(root/'games/mahjong_soul/playbook').rglob('*.py')])}}


def save_new(path, data):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(data,stream,indent=2); stream.write('\n')


def capture_requests(corpus, output):
    from agents.mahjong_soul.call_batch import manifest
    from agents.mahjong_soul.call_counterfactual import capture_calls
    from agents.mahjong_soul.simulation import ENGINE_VERSION
    if Path(output).exists():raise ValueError('Output already exists')
    version = importlib.metadata.version('riichienv')
    if version != ENGINE_VERSION:raise ValueError('Pinned simulator required')
    plan = manifest(corpus,['callers','aggressive']); records = []
    if not plan['eligible_calls']:raise ValueError('No eligible calls')
    source = provenance()
    for match in plan['matches']:
        baseline, targets = capture_calls(match['seed'],match['seat'],opponents=match['profile'])
        golden = json.loads(Path(match['replay']).read_text())
        if baseline['log'] != golden['events']:raise ValueError('Baseline replay changed')
        for case in match['targets']:
            found = [t for t in targets if t['opening'] and not t['value_call']
                     and t['hand_index']==case['hand_index']
                     and t['action']['called_tile']==case['called_tile']
                     and sorted(t['action']['combination'].split('|'))==case['combination']]
            if len(found)!=1:raise ValueError('Expected exactly one public call target')
            target = found[0]
            records.append({k:match[k] for k in ('profile','split','seed','seat')} | case |
                           {'request':target['request'],'action':target['action'],
                            'post_call_discard':target['analysis']['post_call_discard']['tile'],
                            'baseline_exact_replay':True})
        print(json.dumps({'captured':len(records),'total':plan['eligible_calls']}),flush=True)
    save_new(output,{**source,'engine':version,'complete':True,'eligible_calls':plan['eligible_calls'],
                     'scope':'Public requests from exactly reproduced postselected diagnostic matches',
                     'records':records})


def branch_boards(case):
    request = case['request']; board = request['observation']['board']
    action = case['action']
    if action['kind']!='pon' or action not in request['actions']:
        raise ValueError('Expected captured legal Pon')
    post = deepcopy(board)
    for tile in action['combination'].split('|'):post['self']['hand'].remove(tile)
    discard = case['post_call_discard'];post['self']['hand'].remove(discard)
    own = own_player(post)
    own['melds'].append({'type':1,'tiles':action['combination'].split('|')+[action['called_tile']]})
    own['discards'].append({'tile':discard})
    return board,post


def preference(skip, pon):
    if not skip['available'] or not pon['available']:return 'unavailable'
    delta = skip['capped_cycle_cost']-pon['capped_cycle_cost']
    return 'skip' if delta < -1e-10 else 'pon' if delta > 1e-10 else 'tie'


def evaluate_requests(source, output, *, max_states=5000):
    output = Path(output)
    if output.exists():raise ValueError('Output already exists')
    source = Path(source);data = json.loads(source.read_text(encoding='utf-8'))
    if not data['complete'] or len(data['records'])!=data['eligible_calls']:
        raise ValueError('Incomplete request corpus')
    keys = [(r['profile'],r['seed'],r['seat'],r['hand_index']) for r in data['records']]
    if len(keys)!=len(set(keys)) or any(r.get('baseline_exact_replay') is not True for r in data['records']):
        raise ValueError('Duplicate or unverified request')
    report = {**provenance(),'request_corpus_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'request_capture':{k:v for k,v in data.items() if k!='records'},
              'complete':False,'eligible_calls':len(keys),'records':[],
              'scope':'Inspected diagnostic states; not a prospective policy tournament',
              'live_policy_changed':False}
    cache = {}
    # Reserve output before work; a crash retains an explicitly incomplete report.
    save_new(output,report)
    for case in data['records']:
        before,after = branch_boards(case);start = perf_counter();scenarios = {}
        for name,(repairs,rate) in SCENARIOS.items():
            estimates = []
            for board in (before,after):
                key = (json.dumps(board,sort_keys=True),repairs,rate,max_states)
                if key not in cache:
                    cache[key] = estimate_completion(board,ready_repairs=repairs,ron_rate=rate,max_states=max_states)
                estimates.append(cache[key])
            skip,pon = estimates
            scenarios[name] = {'skip':skip,'pon':pon,'preference':preference(skip,pon)}
        report['records'].append({k:v for k,v in case.items() if k!='request'} |
                                  {'board_token':case['request']['board_token'],
                                   'seconds':perf_counter()-start,'scenarios':scenarios})
        report['complete'] = len(report['records'])==len(keys)
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'evaluated':len(report['records']),'total':len(keys)}),flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    capture = sub.add_parser('capture')
    capture.add_argument('--corpus',type=Path,default=Path('logs/mahjong_soul/experiments'))
    capture.add_argument('--output',type=Path,required=True)
    evaluate = sub.add_parser('evaluate')
    evaluate.add_argument('requests',type=Path);evaluate.add_argument('--output',type=Path,required=True)
    evaluate.add_argument('--max-states',type=int,default=5000)
    args = parser.parse_args()
    if args.command=='capture':capture_requests(args.corpus,args.output)
    else:evaluate_requests(args.requests,args.output,max_states=args.max_states)


if __name__=='__main__':main()
