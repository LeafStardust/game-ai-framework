"""Desired client assists; preferences never replace legal-action evaluation.

UI delivery must reconcile observed switch states, not blindly toggle letters.
"""


def assist_preferences(request, action, analysis):
    board=request["observation"]["board"]
    own=next((p for p in board.get("players",[]) if p.get("seat")==board.get("self_seat")),{})
    accepted=own.get("riichi")=="accepted"
    # A route is a current preference, not an irreversible hand commitment.
    # Only accepted Riichi proves that future ordinary draws must be discarded.
    plan=(analysis.get("hand_plan") or {}).get("current")
    route=plan[0] if isinstance(plan,(tuple,list)) and plan else analysis.get("target_route")
    closed=route in {"riichi","chiitoitsu","yakuman_kokushi","yakuman_nine_gates"}
    skip_calls=accepted or (closed and analysis.get("shanten") in (0,1))
    if action["kind"] in {"chi","pon","open_kan","closed_kan","added_kan"}:skip_calls=False
    # North can be part of a pair, triplet or Thirteen Orphans. Do not authorize
    # automatic extraction of future draws from a single favorable offer.
    return {"auto_win":True,"skip_calls":skip_calls,"auto_discard":accepted,
            "auto_kita":False,
            "reason":"accepted_riichi" if accepted else "closed_route_preference" if skip_calls else "keep_options_open",
            "kita_reason":"evaluate_each_offer",
            "delivery":"awaiting_verified_switch_layout"}
