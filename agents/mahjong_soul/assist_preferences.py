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
    # North can be part of a pair, triplet or Thirteen Orphans. Do not authorize
    # automatic extraction of future draws from a single favorable offer.
    return {"auto_win":True,"skip_calls":skip_calls,"auto_discard":accepted,
            "auto_kita":False,
            "reason":"accepted_riichi" if accepted else "keep_options_open",
            "kita_reason":"evaluate_each_offer",
            "delivery":"reviewed_three_player_layout_only"}
