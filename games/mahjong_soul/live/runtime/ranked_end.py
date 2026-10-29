"""Independent ranked end-screen and explicit currency-error evidence."""
import re


def phrase(words,labels,*,lower=False):
    eligible=[w for w in words if 50<=w.get("x",0)<1850 and (600 if lower else 0)<=w.get("y",0)<1040
              and 8<=w.get("height",0)<=90 and 3<=w.get("width",0)<=900]
    for start in range(len(eligible)):
        for size in range(1,7):
            group=eligible[start:start+size]
            if len(group)!=size:continue
            text="".join(re.sub(r"[^a-z0-9]","",w["text"].lower()) for w in group)
            if text not in labels:continue
            left=min(w["x"] for w in group);right=max(w["x"]+w["width"] for w in group)
            top=min(w["y"] for w in group);bottom=max(w["y"]+w["height"] for w in group)
            if right<=1920 and bottom<=1080 and right-left<=900 and bottom-top<=100:
                return round((left+right)/2),round((top+bottom)/2)
    return None


def insufficient_copper(words):
    central=[w for w in words if 250<=w.get("x",0)<=1650 and 200<=w.get("y",0)<=900]
    labels={prefix+currency for prefix in ("insufficient","notenough","insufficientamountof",
            "donthaveenough","donothaveenough","youdonthaveenough","youdonothaveenough")
            for currency in ("copper","coins")}
    return phrase(central,labels)


def queue_active(words):
    return any(re.sub(r"[^a-z]","",w["text"].lower()) in ("cancel","cancelmatch","matching","matchmaking") for w in words)


def final_ranked_screen(words,scores=()):
    exit_point=phrase(words,{"back","return","lobby","returntolobby","backtolobby"},lower=True)
    if exit_point is None:return None
    tokens={re.sub(r"[^a-z0-9]","",w["text"].lower()) for w in words}
    heading=phrase(words,{"matchresults","finalresults","gameresults"})
    placements=len(tokens & {"1st","2nd","3rd","4th"})>=2
    score_matches=len({str(n) for n in scores if type(n) is int} & tokens)>=2
    rating=phrase(words,{"rankpoints","ratingpoints","rankpts","ratingpts"})
    rewards=bool(tokens & {"copper","coins","rewards"})
    return exit_point if heading or placements and score_matches or rating and rewards else None
