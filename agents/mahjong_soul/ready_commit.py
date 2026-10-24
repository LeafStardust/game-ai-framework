"""Explicit policy commitment to an already valuable open ready hand."""
from agents.mahjong_soul.attack_value import own_player


def committed_ready(board,profile):
    if not profile or profile.get("ron_blocked") or not any(m["type"]!=3 for m in own_player(board)["melds"]):return False
    east=board.get("lobby",{}).get("match_length")=="east"
    if east and any(p.get("riichi") in ("declared","accepted") for p in board["players"] if not p.get("is_self")):return False
    # South banks a Mangan-sized ready hand rather than endlessly rebuilding.
    # East locks a broad legal wait for its explicit speed-first objective.
    return (profile.get("dama_ukeire",0)>=(4 if east else 3)
            and profile.get("dama_points",0)>=(1000 if east else 8000))
