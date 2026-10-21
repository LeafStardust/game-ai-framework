"""Exhaustive single-call diagnostics for existing non-first-place replays."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
from agents.mahjong_soul.call_counterfactual import capture_calls,skip_target
from agents.mahjong_soul.simulation import ENGINE_VERSION


def label(tile):
    return {'E':'1z','S':'2z','W':'3z','N':'4z','P':'5z','F':'6z','C':'7z'}.get(tile,
           '0'+tile[1] if tile.endswith('r') else tile)


def openings(events,seat):
    """Read settled openings using public melds/winds, not hidden hands."""
    result=[];opened=False;hand=-1;honors=set()
    for index,event in enumerate(events):
        typ=event['type']
        if typ=='start_kyoku':
            hand+=1;opened=False
            honors={'P','F','C',event['bakaze'],['E','S','W'][(seat-event['oya'])%3]}
        if event.get('actor')!=seat:continue
        if typ=='pon' and not opened and event['pai'] not in honors:
            result.append({'hand_index':hand,'event_index':index,'called_tile':label(event['pai']),
                           'combination':sorted(label(t) for t in event['consumed'])})
        if typ in ('pon','chi','daiminkan','kakan'):opened=True
    return result


def manifest(root,profiles):
    matches=[];scanned=0;nonfirst=0;seen=set()
    for profile in profiles:
        for split in ('development','held-out'):
            folder=Path(root)/f'ready-push-{profile}-{split}'
            data=json.loads((folder/'summary.json').read_text())
            if data['opponents']!=profile:raise ValueError('Corpus opponent profile differs')
            for row in data['records']:
                if row['candidate']!='east_speed':continue
                key=(profile,row['seed'],row['seat'])
                if key in seen:raise ValueError('Duplicate corpus match')
                seen.add(key);scanned+=1
                if row['ranks'][row['seat']]==1:continue
                nonfirst+=1
                replay=folder/f"{row['seed']}-{row['seat']}-east_speed.json"
                saved=json.loads(replay.read_text())
                if saved['metrics']!=row:raise ValueError('Corpus replay metrics differ from summary')
                targets=openings(saved['events'],row['seat'])
                if targets:matches.append({'profile':profile,'split':split,'seed':row['seed'],'seat':row['seat'],
                                           'replay':str(replay),'targets':targets})
    return {'scanned_baseline_matches':scanned,'non_first_matches':nonfirst,
            'eligible_calls':sum(len(m['targets']) for m in matches),'matches':matches}


def run_batch(corpus,output,profiles):
    output=Path(output)
    if output.exists():raise ValueError('Output already exists')
    plan=manifest(corpus,profiles)
    if not plan['eligible_calls']:raise ValueError('No eligible opening calls')
    root=Path(__file__).resolve().parents[2]
    provenance={'revision':subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip(),
                'source_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted([*(root/'agents/mahjong_soul').glob('*.py'),*(root/'games/mahjong_soul/playbook').rglob('*.py')])}}
    output.mkdir(parents=True)
    (output/'manifest.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    records=[]
    for match in plan['matches']:
        profile=match['profile'];seed=match['seed'];seat=match['seat']
        baseline,traced=capture_calls(seed,seat,opponents=profile)
        golden=json.loads(Path(match['replay']).read_text())
        if baseline['log']!=golden['events']:raise ValueError(f'Baseline replay changed: {profile} {seed} {seat}')
        base_name=f'{profile}-{seed}-{seat}-baseline.json'
        (output/base_name).write_text(json.dumps({'metrics':{k:v for k,v in baseline.items() if k!='log'},'events':baseline['log']}),encoding='utf-8')
        for case in match['targets']:
            found=[t for t in traced if t['opening'] and not t['value_call'] and t['hand_index']==case['hand_index']
                   and t['action']['called_tile']==case['called_tile']
                   and sorted(t['action']['combination'].split('|'))==case['combination']]
            if len(found)!=1:raise ValueError('Settled opening does not match exactly one selected public decision')
            target=found[0]
            report,_,skip=skip_target(seed,seat,baseline,target,opponents=profile)
            if report['first_different_event_index']!=case['event_index']:
                raise ValueError('Intervention changed an earlier action or a different call')
            name=f"{profile}-{seed}-{seat}-{case['hand_index']}"
            (output/f'{name}-skip.json').write_text(json.dumps({'events':skip}),encoding='utf-8')
            (output/f'{name}-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            record={'profile':profile,'split':match['split'],'seed':seed,'seat':seat,**case,
                    'board_token':target['request']['board_token'],
                    'target_analysis':{k:target['analysis'].get(k) for k in ('shanten','effective_ukeire','target_route','post_call_discard')},
                    'branches':report['branches'],'exact_target_divergence':True,'baseline_exact_replay':True}
            records.append(record)
            summary={**provenance,'engine':ENGINE_VERSION,'scope':{k:v for k,v in plan.items() if k!='matches'},
                     'complete':len(records)==plan['eligible_calls'],'records':records,
                     'limitation':'Selected losing matches, overlapping calls and reused seeds are correlated diagnostics; never an unbiased win-rate estimate.'}
            (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print(json.dumps({'completed':len(records),'total':plan['eligible_calls'],'profile':profile,'seed':seed,'seat':seat,
                              'hand':case['hand_index'],'pon_wins':report['branches']['pon']['target_hand']['wins'],
                              'skip_wins':report['branches']['skip']['target_hand']['wins']}),flush=True)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,default=Path('logs/mahjong_soul/experiments'))
    parser.add_argument('--profiles',nargs='+',choices=['callers','aggressive'],default=['callers','aggressive'])
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if len(args.profiles)!=len(set(args.profiles)):parser.error('Profiles must be unique')
    if importlib.metadata.version('riichienv')!=ENGINE_VERSION:parser.error('Install the pinned simulator requirements')
    run_batch(args.corpus,args.output,args.profiles)
    return 0


if __name__=='__main__':raise SystemExit(main())
