"""Exact server-bound call menus shared by Chi, Pon and all kan variants."""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, replace
import time

from games.mahjong_soul.live.runtime.calls import plan_chi, plan_pon, ChiMenuExecutor
from games.mahjong_soul.live.runtime.kan import plan_concealed_kan, plan_open_kan, plan_added_kan
from games.mahjong_soul.live.runtime.input import board_token

CODES={"chi":2,"pon":3,"closed_kan":4,"open_kan":5,"added_kan":6}
PLANNERS={"chi":plan_chi,"pon":plan_pon,"closed_kan":plan_concealed_kan,
          "open_kan":plan_open_kan,"added_kan":plan_added_kan}


@dataclass(frozen=True)
class CallMenuPlan:
    token: str
    connection: str
    step: int
    seat: int
    kind: str
    combination: str
    combinations: tuple
    x: float
    y: float
    width: int
    height: int
    expires: float


class CallMenuExecutor(ChiMenuExecutor):
    pass


def offer(report, action):
    state=report.get("state") or {}
    operation=state.get("operations") or {}
    choices=[o for o in operation.get("operation_list",[]) if o.get("type")==CODES.get(action.get("kind"))]
    if (not report.get("state_ready") or not report.get("connection_open")
            or operation.get("seat")!=state.get("seat") or len(choices)!=1
            or action.get("combination") not in choices[0].get("combination",[])):
        raise ValueError("Exact call combination is not offered to this player")
    combinations=choices[0]["combination"]
    if len(set(combinations))!=len(combinations):raise ValueError("Duplicate call combinations")
    return combinations


def selected_call(report, profile, action, *, now=None):
    """Validate selected contributions with existing canonical call planners.

    Only the operation's candidate list is narrowed, never the real board token
    used for delivery/confirmation. All other offers, exact tile identities,
    source discard, existing Pon and hand-copy checks remain in effect.
    """
    offer(report,action)
    narrowed=deepcopy(report)
    code=CODES[action["kind"]]
    next(o for o in narrowed["state"]["operations"]["operation_list"] if o["type"]==code)["combination"]=[action["combination"]]
    plan=PLANNERS[action["kind"]](narrowed,profile,now=now)
    return replace(plan,token=board_token(report))


def plan_call(report, profile, action, *, now=None):
    combinations=offer(report,action)
    if profile.get("stage")!="call_offer":raise ValueError("Call button stage is required")
    final=selected_call(report,profile,action,now=now)
    if len(combinations)==1:return final
    return CallMenuPlan(final.token,final.connection,final.step,final.seat,
                        action["kind"],action["combination"],tuple(combinations),
                        final.x,final.y,final.width,final.height,final.expires)


def plan_call_choice(report, profile, action, *, now=None):
    combinations=offer(report,action)
    visible=profile.get("combinations",[])
    points=profile.get("choice_points",[])
    # The UI can reorder server options; match contributions, never indices.
    def key(value):return tuple(sorted(value.split("|")))
    if (profile.get("stage")!="call_choices" or len(combinations)<2
            or len(points)!=len(visible) or len(visible)!=len(combinations)
            or Counter(map(key,visible))!=Counter(map(key,combinations))
            or len(set(map(key,visible)))!=len(visible)):
        raise ValueError("Visible call choices do not uniquely match the full server offer")
    index=list(map(key,visible)).index(key(action["combination"]))
    bound=dict(profile,stage="call_offer")
    bound["chi" if action["kind"]=="chi" else "pon" if action["kind"]=="pon" else "kan"]=points[index]
    return selected_call(report,bound,action,now=now)


def validate_continuation(pending, plan, report, *, now=None):
    if board_token(report)!=pending.token or (plan.width,plan.height)!=(pending.width,pending.height):
        raise ValueError("Call menu board or geometry changed")
    action={"kind":pending.kind,"combination":pending.combination}
    if tuple(offer(report,action))!=pending.combinations:raise ValueError("Call menu offer changed")
    field="chi" if pending.kind=="chi" else "pon" if pending.kind=="pon" else "kan"
    profile={"version":1,"verified":True,"stage":"call_offer","client_size":[plan.width,plan.height],
             "operation_types":[o["type"] for o in report["state"]["operations"]["operation_list"]],field:[plan.x,plan.y]}
    expected=selected_call(report,profile,action,now=now)
    if replace(expected,expires=plan.expires)!=plan:
        raise ValueError("Selected call does not match the intended menu combination")
