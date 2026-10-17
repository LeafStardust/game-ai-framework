"""Summarize an agent recording without dumping raw network credentials."""
import argparse
import json
from pathlib import Path


def summarize(directory):
    directory=Path(directory);counts={};issues=[];last_action=None;image=None;heartbeat=None;configuration=None
    with (directory/"events.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            try:row=json.loads(line)
            except ValueError:issues.append({"kind":"incomplete_log_row"});continue
            kind=row.get("kind");counts[kind]=counts.get(kind,0)+1
            if kind=="configuration":configuration={k:row.get(k) for k in ("playstyle","revision","source_hashes")}
            if kind=="frame":image=row.get("image")
            if kind=="heartbeat":heartbeat={k:row.get(k) for k in ("timestamp","controller","halted")}
            if kind in ("decision","submitted"):last_action=row.get("event",row.get("action"))
            if kind in ("error","blocked","input_failure","preflight_failed"):
                issue={k:row[k] for k in ("kind","reason","image","board_token","sequence") if k in row}
                issue.setdefault("image",image);issues.append(issue)
    return {"directory":str(directory),"counts":counts,"last_action":last_action,"recent_issues":issues[-10:],"heartbeat":heartbeat,"configuration":configuration}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("directory",nargs="?",type=Path)
    args=parser.parse_args();directory=args.directory
    if directory is None:
        root=Path(__file__).resolve().parents[2]/"logs/mahjong_soul/sessions"
        paths=[p for p in root.glob("*") if (p/"events.jsonl").is_file()]
        if not paths:parser.error("No agent recordings yet")
        directory=max(paths,key=lambda p:p.name)
    print(json.dumps(summarize(directory),indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
