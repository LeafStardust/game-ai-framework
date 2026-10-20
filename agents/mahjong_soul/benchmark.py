"""Observed match outcomes from local recordings; no simulated win-rate claims."""
import argparse
from collections import Counter
import json
import math
import hashlib
from pathlib import Path


def rate(success,total):
    if not total:return {"successes":success,"total":total,"rate":None,"wilson_95":None}
    p=success/total;z=1.959963984540054;den=1+z*z/total
    center=(p+z*z/(2*total))/den
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return {"successes":success,"total":total,"rate":p,"wilson_95":[max(0,center-half),min(1,center+half)]}


def benchmark(paths):
    games={};bad=0
    for path in paths:
        revision="unknown";current=None
        with Path(path).open(encoding="utf-8") as stream:
            for line in stream:
                try:r=json.loads(line)
                except ValueError:bad+=1;continue
                kind=r.get("kind")
                if kind=="configuration":revision=r.get("revision","unknown")
                report=r.get("report") or {};state=report.get("state") or {}
                connection=report.get("game_connection") or r.get("connection")
                if connection:
                    current=connection
                    g=games.setdefault(current,{"connection":current,"revisions":set(),"sessions":set(),"seat":None,"players":None,"lobby":None,"ai":None,"complete":False,"scores":None,"rounds":{},"active":None,"seen":set(),"issues":Counter(),"playbooks":set()})
                    g["sessions"].add(Path(path).parent.name);g["revisions"].add(revision)
                    if state:
                        g["seat"]=state.get("seat",g["seat"]);g["players"]=state.get("player_count",g["players"])
                        g["lobby"]=state.get("lobby",g["lobby"])
                        if state.get("status")=="match_ended":g["complete"]=True;g["scores"]=state.get("scores")
                if current is None:continue
                g=games[current]
                if kind=="ai_room_verified":g["ai"]=r.get("verified")
                if kind in ("blocked","error","retry_delivered"):g["issues"][kind]+=1
                if kind=="decision":
                    a=r.get("event",{}).get("analysis",{})
                    if a.get("playbook"):g["playbooks"].add((a["playbook"],a.get("playbook_version")))
                    round_key=g["active"]
                    if round_key in g["rounds"] and a.get("shanten")==0 and a.get("effective_ukeire",0)>0:
                        hand=g["rounds"][round_key]
                        if hand["first_recommended_tenpai_discard"] is None:
                            action=r["event"].get("action",{})
                            hand["first_recommended_tenpai_discard"]=hand["self_discards"]+int(action.get("kind") in ("discard","riichi"))
                    continue
                if kind!="game_event":continue
                event=r.get("event",{});name=event.get("name");d=event.get("data",{})
                if event.get("source") not in ("live","restore"):continue
                if name=="ActionNewRound":
                    key=tuple(d.get(k,0) for k in ("chang","ju","ben"));g["active"]=key
                    g["rounds"].setdefault(key,{"round":key,"ended":False,"win":False,"deal_in":False,"self_discards":0,"first_recommended_tenpai_discard":None,"last_discard":None})
                hand=g["rounds"].get(g["active"])
                if hand is None:continue
                key=(g["active"],name,event.get("step"))
                if key in g["seen"]:continue
                g["seen"].add(key)
                if name=="ActionDiscardTile":
                    hand["last_discard"]=d.get("seat")
                    if d.get("seat")==g["seat"]:hand["self_discards"]+=1
                if name in ("ActionHule","ActionNoTile","ActionLiuJu"):
                    hand["ended"]=True
                    if name=="ActionHule":
                        winners=d.get("hules",[])
                        hand["win"]=any(h.get("seat")==g["seat"] for h in winners)
                        hand["deal_in"]=hand["last_discard"]==g["seat"] and any(not h.get("zimo") and h.get("seat")!=g["seat"] for h in winners)
    matches=[]
    for g in games.values():
        if not g["rounds"]:continue
        hands=list(g["rounds"].values());ended=[h for h in hands if h["ended"]]
        scores=g["scores"];seat=g["seat"]
        valid_scores=isinstance(scores,list) and isinstance(seat,int) and seat<len(scores) and all(type(n) is int for n in scores)
        full=g["complete"] and (0,0,0) in g["rounds"] and all(h["ended"] for h in hands) and valid_scores
        rank=1+sum(n>scores[seat] for n in scores) if full else None
        tied=full and scores.count(scores[seat])>1
        matches.append({"connection":g["connection"],"sessions":sorted(g["sessions"]),"revisions":sorted(g["revisions"]),"playbooks":sorted(g["playbooks"]),"lobby":g["lobby"],"ai":g["ai"],"player_count":g["players"],"complete":full,"rank_by_score":rank,"score_tie":bool(tied),"final_score":scores[seat] if full else None,"round_details":hands,"hands":len(ended),"hand_wins":sum(h["win"] for h in ended),"deal_ins":sum(h["deal_in"] for h in ended),"recommended_tenpai_discards":[h["first_recommended_tenpai_discard"] for h in ended if h["first_recommended_tenpai_discard"] is not None],"issues":dict(g["issues"])})
    groups={}
    for m in matches:
        if not m["complete"]:continue
        lobby=m["lobby"] or {}
        rules=hashlib.sha256(json.dumps(lobby.get("rule_details",{}),sort_keys=True).encode()).hexdigest()[:16]
        key=json.dumps([m["player_count"],lobby.get("match_length"),m["ai"],rules,m["revisions"],m["playbooks"]])
        groups.setdefault(key,[]).append(m)
    aggregates=[]
    for key,items in groups.items():
        turns=[n for m in items for n in m["recommended_tenpai_discards"]];hands=sum(m["hands"] for m in items)
        untied=[m for m in items if not m["score_tie"]]
        aggregates.append({"group":json.loads(key),"matches":len(items),"hands":hands,"first_place":rate(sum(m["rank_by_score"]==1 for m in untied),len(untied)),"last_place":rate(sum(m["rank_by_score"]==m["player_count"] for m in untied),len(untied)),"hand_win":rate(sum(m["hand_wins"] for m in items),hands),"deal_in":rate(sum(m["deal_ins"] for m in items),hands),"average_rank_untied":sum(m["rank_by_score"] for m in untied)/len(untied) if untied else None,"recommended_tenpai_discard_mean":sum(turns)/len(turns) if turns else None,"recommended_tenpai_hands":len(turns),"recommended_tenpai_reach":rate(len(turns),hands),"issues":dict(sum((Counter(m["issues"]) for m in items),Counter()))})
    return {"version":1,"mode":"observed_recordings","malformed_rows":bad,"matches":matches,"groups":aggregates,"limitations":["Observational data, not a simulator or a causal policy comparison.","Partial matches excluded from aggregates; halted matches included with issue counts if capture reaches match end.","Tenpai speed is the first recorded positive-copy Tenpai recommendation in each hand, not exhaustive server-confirmed Tenpai timing.","Score ties excluded from placement averages and first-place rates; reconnect fragments may be excluded as incomplete.","Grouping separates player count, East/South, AI verification, revisions and playbook versions. Manual interventions and opponent strength are not controlled."]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions",type=Path,default=Path(__file__).resolve().parents[2]/"logs/mahjong_soul/sessions")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args();result=benchmark(sorted(args.sessions.glob("*/events.jsonl")))
    encoded=json.dumps(result,indent=2)+"\n"
    if args.output:args.output.write_text(encoded,encoding="utf-8")
    else:print(encoded,end="")
    return 0


if __name__=="__main__":raise SystemExit(main())
