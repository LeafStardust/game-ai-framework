"""Seeded Sanma experiments; engine owns legality, settlement and hidden tiles."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import subprocess
from agents.mahjong_soul.efficiency import rank_discards
from agents.mahjong_soul.policy import make_policy


ENGINE_VERSION="0.4.10"
KINDS=[str(n)+s for s in "mps" for n in range(1,10)]+[str(n)+"z" for n in range(1,8)]


def tile(value):
    if value in (16,52,88):return "0"+"mps"[(value//4)//9]
    return KINDS[value//4]


def kind(value):return "5"+value[1:] if value.startswith("0") else value


def events(obs):
    return [json.loads(e) if isinstance(e,str) else e for e in obs.events]


def request(obs,history=None):
    """Use only the observing seat's public observation, never env.hands/wall."""
    from riichienv import calculate_shanten_3p
    d=obs.to_dict();pid=d["player_id"];history=events(obs) if history is None else history
    start=next(e for e in reversed(history) if e["type"]=="start_kyoku")
    index=history.index(start);history=history[index:];norths=[0]*3
    for e in history:
        if e["type"]=="kita":norths[e["actor"]]+=1
    all_meld_ids={t for group in obs.melds for m in group for t in m.tiles}
    visible_ids=set(obs.hand)|set(d["dora_indicators"])|all_meld_ids|{t for river in d["discards"] for t in river}
    visible=Counter(kind(tile(t)) for t in visible_ids);visible["4z"]+=sum(norths)
    players=[]
    for seat in range(3):
        melds=[{"type":{"Chi":0,"Pon":1,"Daiminkan":2,"Ankan":3,"Kakan":2}[str(m.meld_type).split(".")[-1]],"tiles":[tile(t) for t in m.tiles]} for m in obs.melds[seat]]
        players.append({"seat":seat,"is_self":seat==pid,"score":d["scores"][seat],"melds":melds,"norths":norths[seat],"riichi":"accepted" if d["riichi_declared"][seat] else "none","discards":[{"tile":tile(t),"called":t in all_meld_ids,"tsumogiri":bool(obs.tsumogiri_flags[seat][i]) if i<len(obs.tsumogiri_flags[seat]) else None,"riichi":obs.riichi_sutehais[seat]==t} for i,t in enumerate(d["discards"][seat])]})
    actions=[];bindings=[];codes=[];native=obs.legal_actions()
    for a in native:
        typ=int(a.action_type);intent=None
        if typ==0:intent={"kind":"discard","tile":tile(a.tile)}
        elif typ==5:
            for discard in native:
                if int(discard.action_type)!=0:continue
                hand=list(obs.hand);hand.remove(discard.tile)
                if calculate_shanten_3p(hand)==0:
                    choice={"kind":"riichi","tile":tile(discard.tile)};actions.append(choice);bindings.append((choice,a))
            continue
        elif typ in (2,3,8,9):
            name={2:"pon",3:"open_kan",8:"closed_kan",9:"added_kan"}[typ]
            consume=[tile(t) for t in a.consume_tiles]
            if typ==9:
                meld=next(m for m in players[pid]["melds"] if m["type"]==1 and kind(m["tiles"][0])==kind(tile(a.tile)))
                consume=list(meld["tiles"])+[tile(a.tile)]
            intent={"kind":name,"combination":"|".join(consume)}
            if typ in (2,3):intent["called_tile"]=tile(a.tile)
        elif typ==7:intent={"kind":"skip"}
        elif typ==11:intent={"kind":"extract_north"}
        elif typ in (4,6):continue # Claimed directly from engine-legal actions.
        elif typ==10:continue # Optional Nine Terminals abort is not a policy action.
        else:raise ValueError(f"Unmapped simulator action {typ}")
        actions.append(intent);bindings.append((intent,a))
        code={0:1,2:3,3:5,8:4,9:6,11:11}.get(typ)
        if code:codes.append({"type":code,"combination":[intent["combination"]] if "combination" in intent else []})
    reaches=[a["tile"] for a in actions if a["kind"]=="riichi"]
    if reaches:codes.append({"type":7,"combination":reaches})
    opening=start["tehais"][pid]
    def mjtile(t):return {"E":"1z","S":"2z","W":"3z","N":"4z","P":"5z","F":"6z","C":"7z"}.get(t,"0"+t[1] if t.endswith("r") else t)
    drawn=obs.drawn_tile
    board={"player_count":3,"self_seat":pid,"self":{"hand":[tile(t) for t in obs.hand],"opening_hand":[mjtile(t) for t in opening],"drawn_tile":tile(drawn) if drawn is not None else None,"furiten":False,"scoring_context":{"history_complete":False,"win":{}}},"players":players,"round":{"chang":d["round_wind"],"ju":start["oya"],"ben":d["honba"],"liqibang":d["riichi_sticks"]},"wall_remaining":55-sum(e["type"]=="tsumo" for e in history),"dora_indicators":[tile(t) for t in d["dora_indicators"]],"rules":{"open_tanyao":True,"tsumo_loss":True},"visible_tile_counts":dict(visible),"visibility_complete":True,"available_operations":{"seat":pid,"operation_list":codes},"lobby":{"identified":True,"player_count":3,"match_length":"east","label":"3 Player East Wind","unsupported_rules":[]}}
    token=hashlib.sha256(json.dumps(board,sort_keys=True).encode()).hexdigest()
    return {"board_token":token,"observation":{"board":board,"source":{"connection":"offline","generation":1}},"actions":actions},bindings


class Agent:
    def __init__(self,name):
        if name not in ("efficiency","east_speed","east_speed_push","east_speed_lookahead","east_speed_two_draw","east_speed_development","east_speed_partial_yaku","east_speed_ready_push"):
            raise ValueError("Unknown simulation candidate")
        self.name=name;self.policy=make_policy("playbook","atk") if name in ("east_speed","east_speed_push","east_speed_lookahead","east_speed_two_draw","east_speed_development","east_speed_partial_yaku","east_speed_ready_push") else None
        if name=="east_speed_push":
            # Experiment only: isolate the cost of giving up winning progress
            # against Riichi. Never change production playbook factories.
            book=self.policy.registry.get(3,"atk","east")
            book.strategy["defense"]["always_push"]=True
        if name=="east_speed_lookahead":
            self.policy.registry.get(3,"atk","east").strategy["discard_value"]["next_wait_tiebreak"]=True
        if name=="east_speed_two_draw":
            self.policy.registry.get(3,"atk","east").strategy["discard_value"]["two_draw_progress"]=True
        if name=="east_speed_development":
            self.policy.registry.get(3,"atk","east").strategy["discard_value"]["early_development"]=True
        if name=="east_speed_partial_yaku":
            # Frozen old gate for offline comparison with exact legal scoring.
            self.policy.registry.get(3,"atk","east").strategy["defense"]["allow_scored_ready_yaku"]=False
        if name=="east_speed_ready_push":
            self.policy.registry.get(3,"atk","east").strategy["defense"].update(
                ready_push_max_danger=90,ready_push_min_ukeire=3)
        self.reach_tile=None
        self.history=[]

    def act(self,obs):
        self.history.extend(events(obs))
        legal=obs.legal_actions()
        wins=[a for a in legal if int(a.action_type) in (4,6)]
        if wins:return wins[0]
        if self.reach_tile is not None:
            action=next((a for a in legal if int(a.action_type)==0 and tile(a.tile)==self.reach_tile),None)
            if action is None:raise ValueError("Riichi continuation differs from intended tile")
            self.reach_tile=None;return action
        req,bindings=request(obs,self.history)
        if self.policy:chosen=self.policy.choose(req)
        else:
            north=next((a for a in req["actions"] if a["kind"]=="extract_north"),None)
            ds=[a for a in req["actions"] if a["kind"]=="discard"]
            if north:chosen=north
            elif ds:
                chosen=rank_discards(req)[0]["action"]
                reach=next((a for a in req["actions"] if a["kind"]=="riichi" and a["tile"]==chosen["tile"]),None)
                chosen=reach or chosen
            else:chosen=next(a for a in req["actions"] if a["kind"]=="skip")
        result=next((native for intent,native in bindings if intent==chosen),None)
        if result is None:raise ValueError("Policy action has no exact engine-legal binding")
        if chosen["kind"]=="riichi":self.reach_tile=chosen["tile"]
        return result


OPPONENT_PROFILES={
    "efficiency":("efficiency","efficiency"),
    "callers":("east_speed","east_speed"),
    "aggressive":("east_speed_push","east_speed_push"),
    "mixed":("east_speed","east_speed_push"),
}


def seat_policies(seat,candidate,opponents):
    if seat not in range(3):raise ValueError("Seat must be 0, 1 or 2")
    if opponents not in OPPONENT_PROFILES:raise ValueError("Unknown opponent profile")
    names={seat:candidate}
    for offset,name in enumerate(OPPONENT_PROFILES[opponents],start=1):names[(seat+offset)%3]=name
    return names


def run(seed,seat,candidate,*,mode="3p-red-east",max_steps=5000,opponents="efficiency"):
    from riichienv import RiichiEnv,GameRule
    names=seat_policies(seat,candidate,opponents)
    env=RiichiEnv(game_mode=mode,seed=seed,rule=GameRule.default_mjsoul())
    observations=env.reset();speed={};agents={p:Agent(names[p]) for p in range(3)}
    action_counts=[Counter() for _ in range(3)]
    initial=env.mjai_log[:];steps=0;started=time.monotonic();decision_seconds=0
    while not env.done():
        if steps>=max_steps:raise ValueError("Simulator step limit reached; no partial result accepted")
        tick=time.monotonic();actions={pid:agents[pid].act(obs) for pid,obs in observations.items()}
        for pid,action in actions.items():action_counts[pid][str(int(action.action_type))]+=1
        if seat in actions and int(actions[seat].action_type)==0:
            from riichienv import calculate_shanten_3p
            start=next(e for e in reversed(agents[seat].history) if e["type"]=="start_kyoku")
            key=(start["bakaze"],start["kyoku"],start["honba"])
            track=speed.setdefault(key,{"self_discards":0,"first_shape_tenpai_discard":None})
            track["self_discards"]+=1
            hand=list(observations[seat].hand);hand.remove(actions[seat].tile)
            if calculate_shanten_3p(hand)==0 and track["first_shape_tenpai_discard"] is None:
                track["first_shape_tenpai_discard"]=track["self_discards"]
        decision_seconds+=time.monotonic()-tick
        if not actions:raise ValueError("No simulator actions before game end")
        observations=env.step(actions);steps+=1
    history=env.mjai_log;hands=sum(e["type"]=="end_kyoku" for e in history)
    wins=sum(e["type"]=="hora" and e.get("actor")==seat for e in history)
    hand_index=-1;deal_in_hands=set()
    for event in history:
        if event["type"]=="start_kyoku":hand_index+=1
        if event["type"]=="hora" and event.get("target")==seat and event.get("actor")!=seat:deal_in_hands.add(hand_index)
    dealins=len(deal_in_hands)
    return {"seed":seed,"seat":seat,"candidate":candidate,"opponent_profile":opponents,"opponents_by_seat":{str(p):name for p,name in names.items() if p!=seat},"action_counts":action_counts,"scores":env.scores(),"ranks":env.ranks(),"hands":hands,"wins":wins,"deal_ins":dealins,"shape_tenpai_discards":[v["first_shape_tenpai_discard"] for v in speed.values() if v["first_shape_tenpai_discard"] is not None],"steps":steps,"seconds":time.monotonic()-started,"decision_seconds":decision_seconds,"initial_deal_digest":hashlib.sha256(json.dumps(initial,sort_keys=True).encode()).hexdigest(),"log":history}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--seeds",type=int,nargs="+",default=[0]);parser.add_argument("--seats",type=int,nargs="+",default=[0,1,2]);parser.add_argument("--candidates",nargs="+",choices=["efficiency","east_speed","east_speed_push","east_speed_lookahead","east_speed_two_draw","east_speed_development","east_speed_partial_yaku","east_speed_ready_push"],default=["efficiency","east_speed"]);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--single-hand",action="store_true")
    parser.add_argument("--opponents",choices=list(OPPONENT_PROFILES),default="efficiency")
    args=parser.parse_args()
    if any(s not in range(3) for s in args.seats):parser.error("Seats must be 0, 1 or 2")
    if any(seed<0 for seed in args.seeds):parser.error("Seeds must be nonnegative")
    if any(len(values)!=len(set(values)) for values in (args.seeds,args.seats,args.candidates)):
        parser.error("Seeds, seats and candidates must be unique")
    if importlib.metadata.version("riichienv")!=ENGINE_VERSION:parser.error("Install the pinned simulator requirements")
    if (args.output/"summary.json").exists():parser.error("Output already contains an experiment; choose a new directory")
    revision=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
    source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    policy_digest=hashlib.sha256()
    root=Path(__file__).resolve().parents[2]
    for source in sorted([*(root/"agents/mahjong_soul").glob("*.py"),*(root/"games/mahjong_soul/playbook").rglob("*.py")]):
        policy_digest.update(str(source.relative_to(root)).encode());policy_digest.update(source.read_bytes())
    args.output.mkdir(parents=True,exist_ok=True);records=[];mode="3p-red-single" if args.single_hand else "3p-red-east"
    for seed in args.seeds:
        for seat in args.seats:
            digest=None
            for candidate in args.candidates:
                result=run(seed,seat,candidate,mode=mode,opponents=args.opponents)
                if digest is not None and digest!=result["initial_deal_digest"]:raise ValueError("Paired starting deals differ")
                digest=result["initial_deal_digest"]
                log=result.pop("log");path=args.output/f"{seed}-{seat}-{candidate}.json"
                path.write_text(json.dumps({"metrics":result,"events":log},indent=2),encoding="utf-8");records.append(result)
                print(json.dumps(result),flush=True)
                (args.output/"summary.json").write_text(json.dumps({"engine":ENGINE_VERSION,"mode":mode,"opponents":args.opponents,"rules":"GameRule.default_mjsoul; preset flow 3p-red-east or single","revision":revision,"adapter_sha256":source_hash,"policy_tree_sha256":policy_digest.hexdigest(),"records":records,"limitation":"Small samples are smoke tests; engine defaults are not verified identical to every Steam room. Divergent actions change later draws."},indent=2),encoding="utf-8")
    return 0


if __name__=="__main__":raise SystemExit(main())
