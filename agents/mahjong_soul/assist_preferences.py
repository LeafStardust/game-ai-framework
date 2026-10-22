"""Desired client assists; preferences never replace legal-action evaluation.

UI delivery must reconcile observed switch states, not blindly toggle letters.
"""


def assist_preferences(request, action, analysis):
    board=request["observation"]["board"]
    own=next((p for p in board.get("players",[]) if p.get("seat")==board.get("self_seat")),{})
    accepted=own.get("riichi")=="accepted"
    # A chosen closed route is provisional. Even one-Shanten closed hands
    # can gain legal Tenpai from a Yakuhai Pon, so keep those offers visible.
    # Accepted Riichi is the only current irreversible closed commitment.
    skip_calls=accepted
    hand=board.get("self",{}).get("hand",[])
    route=str(analysis.get("target_route", ""))
    plan=(analysis.get("hand_plan") or {}).get("current") or []
    protect_north=(route in ("yakuman_kokushi","yakuman_all_honors")
                   or any(p in ("yakuman_kokushi","yakuman_all_honors") for p in plan)
                   or hand.count("4z")>=2
                   or ("4z" in hand and action.get("kind")!="extract_north" and not accepted))
    auto_kita=board.get("player_count")==3 and not protect_north
    return {"auto_win":True,"skip_calls":skip_calls,"auto_discard":accepted,
            "auto_kita":auto_kita,
            "reason":"accepted_riichi" if accepted else "keep_options_open",
            "kita_reason":"north_required_in_hand" if protect_north else "automatic_sanma_extraction",
            "delivery":"reviewed_three_player_layout_only"}
