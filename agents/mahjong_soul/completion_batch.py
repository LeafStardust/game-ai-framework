"""Apply completion models to every opening in the existing diagnostic corpus."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from agents.mahjong_soul.call_batch import manifest
from agents.mahjong_soul.call_counterfactual import capture_calls
from agents.mahjong_soul.compare_completion_speed import compare_request


def evaluate(corpus, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Output already exists')
    plan = manifest(corpus, ['callers', 'aggressive'])
    root = Path(__file__).resolve().parents[2]
    source = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted([*(root/'agents/mahjong_soul').glob('*.py'),
                               *(root/'games/mahjong_soul/playbook').rglob('*.py')])}
    records = []
    def save():
        output.write_text(json.dumps({'complete': len(records) == plan['eligible_calls'],
            'eligible_calls': plan['eligible_calls'], 'records': records,
            'revision': subprocess.run(['git','rev-parse','HEAD'], capture_output=True,
                                        text=True, check=True).stdout.strip(),
            'source_hashes': source,
            'scope': 'Postselected diagnostic calls, not a policy tournament'}, indent=2)+'\n', encoding='utf-8')
    for match in plan['matches']:
        baseline, targets = capture_calls(match['seed'], match['seat'], opponents=match['profile'])
        golden = json.loads(Path(match['replay']).read_text())
        if baseline['log'] != golden['events']:
            raise ValueError('Baseline replay changed')
        for case in match['targets']:
            found = [t for t in targets if t['opening'] and not t['value_call']
                     and t['hand_index'] == case['hand_index']
                     and t['action']['called_tile'] == case['called_tile']
                     and sorted(t['action']['combination'].split('|')) == case['combination']]
            if len(found) != 1:
                raise ValueError('Public opening does not match exactly one target')
            report = compare_request(found[0]['request'])
            records.append({k: match[k] for k in ('profile','split','seed','seat')} |
                           case | {'baseline_exact_replay': True} | report)
            save()
            print(json.dumps({'completed': len(records), 'total': plan['eligible_calls']}), flush=True)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=Path('logs/mahjong_soul/experiments'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.corpus, args.output)


if __name__ == '__main__':
    main()
