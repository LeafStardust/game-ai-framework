"""Paired, seed-level summaries; experimental variants never alter live policy."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random


def summarize(records):
    hands=sum(r["hands"] for r in records)
    turns=[t for r in records for t in r.get("shape_tenpai_discards",[])]
    return {"matches":len(records),"hands":hands,
            "first_place_rate":sum(r["ranks"][r["seat"]]==1 for r in records)/len(records),
            "average_rank":sum(r["ranks"][r["seat"]] for r in records)/len(records),
            "hand_win_rate":sum(r["wins"] for r in records)/hands,
            "deal_in_rate":sum(r["deal_ins"] for r in records)/hands,
            "shape_tenpai_reach_rate":len(turns)/hands,
            "conditional_shape_tenpai_discard_mean":sum(turns)/len(turns) if turns else None}


def compare(data,baseline="east_speed",candidate="east_speed_push"):
    pairs=defaultdict(dict)
    for record in data["records"]:
        if record["candidate"] not in (baseline,candidate):continue
        key=(record["seed"],record["seat"])
        if record["candidate"] in pairs[key]:raise ValueError("Duplicate seed/seat/policy result")
        pairs[key][record["candidate"]]=record
    if not pairs or any(set(pair)!={baseline,candidate} for pair in pairs.values()):raise ValueError("Every seed/seat must have both candidates")
    for pair in pairs.values():
        if pair[baseline]["initial_deal_digest"]!=pair[candidate]["initial_deal_digest"]:raise ValueError("Paired starting deals differ")
        for key in ("opponent_profile","opponents_by_seat"):
            if pair[baseline].get(key)!=pair[candidate].get(key):raise ValueError("Paired opponents differ")
    base=summarize([p[baseline] for p in pairs.values()]);other=summarize([p[candidate] for p in pairs.values()])
    seeds=sorted({key[0] for key in pairs});per_seed=[]
    metrics=("first_place_rate","average_rank","hand_win_rate","deal_in_rate","shape_tenpai_reach_rate")
    for seed in seeds:
        a=summarize([p[baseline] for key,p in pairs.items() if key[0]==seed]);b=summarize([p[candidate] for key,p in pairs.items() if key[0]==seed])
        per_seed.append({"seed":seed,**{metric:b[metric]-a[metric] for metric in metrics}})
    intervals={};rng=random.Random(0)
    if len(seeds)>=2:
        for metric in metrics:
            estimates=sorted(sum(rng.choice(per_seed)[metric] for _ in seeds)/len(seeds) for _ in range(2000))
            intervals[metric]=[estimates[49],estimates[1949]]
    return {"baseline":baseline,"candidate":candidate,"engine":data.get("engine"),"opponents":data.get("opponents"),"revision":data.get("revision"),"policy_tree_sha256":data.get("policy_tree_sha256"),"mode":data.get("mode"),"independent_seeds":len(seeds),"paired_seat_assignments":len(pairs),"baseline_metrics":base,"candidate_metrics":other,"per_seed_candidate_minus_baseline":per_seed,"seed_cluster_bootstrap_95":intervals,"limitations":["Exploratory intervals from very few seeds are unstable; they are not proof of superiority.","Seat assignments and hands within a seed are correlated; resampling is by seed.","Tenpai discard mean is conditional on reaching shape Tenpai, not a legal-win guarantee.","Fixed heuristic opponents do not represent Steam AI or human opponents."]}


def replay_coverage(summary,baseline,candidate):
    data=json.loads(Path(summary).read_text());pairs={}
    for row in data["records"]:
        if row["candidate"] in (baseline,candidate):pairs.setdefault((row["seed"],row["seat"]),{})[row["candidate"]]=row
    changed=0;checked=0;missing=0
    for (seed,seat),pair in pairs.items():
        if set(pair)!={baseline,candidate}:continue
        paths=[Path(summary).parent/f"{seed}-{seat}-{name}.json" for name in (baseline,candidate)]
        if not all(path.is_file() for path in paths):missing+=1;continue
        logs=[json.loads(path.read_text())["events"] for path in paths]
        checked+=1;changed+=logs[0]!=logs[1]
    return {"checked_pairs":checked,"different_replays":changed,"missing_pairs":missing,
            "candidate_exercised":changed>0,
            "note":"Identical replays provide no observed action-change exposure; outcome equality is not proof of general equivalence."}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("summary",type=Path);parser.add_argument("--baseline",default="east_speed");parser.add_argument("--candidate",default="east_speed_push");parser.add_argument("--output",type=Path)
    args=parser.parse_args();data=compare(json.loads(args.summary.read_text()),args.baseline,args.candidate);data["replay_coverage"]=replay_coverage(args.summary,args.baseline,args.candidate);text=json.dumps(data,indent=2)+"\n"
    if args.output:args.output.write_text(text,encoding="utf-8")
    else:print(text,end="")


if __name__=="__main__":main()
