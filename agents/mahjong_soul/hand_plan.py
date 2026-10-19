"""Round-scoped route memory; observations never acquire mutable policy state."""

def begin(owner,request):
    board=request["observation"]["board"];source=request["observation"].get("source",{})
    key=(source.get("connection"),source.get("generation"),*(board["round"].get(k,0) for k in ("chang","ju","ben")))
    if getattr(owner,"_plan_round",None)!=key:
        owner._plan_round=key;owner._hand_plan=None
    return owner._hand_plan


def remember(owner,option):
    previous=owner._hand_plan
    if option and option.get("target_route"):
        owner._hand_plan=(option["target_route"],option.get("target_suit") or option.get("yakuman_suit"))
    return {"previous":previous,"current":owner._hand_plan,
            "transition":"start" if previous is None and owner._hand_plan else
                         "switch" if previous!=owner._hand_plan else "retain"}
