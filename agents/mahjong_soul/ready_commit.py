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


def kan_possible(board):
    """Keep client C/D from consuming a present or still-live fourth tile."""
    from collections import Counter
    from agents.mahjong_soul.efficiency import tile_supply
    from games.mahjong_soul.live.runtime.kan import tile_kind
    own=next((p for p in board.get("players",[]) if p.get("seat")==board.get("self_seat")),{})
    counts=Counter(tile_kind(t) for t in board.get("self",{}).get("hand",[]))
    if not counts or "visible_tile_counts" not in board:return False
    visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    def unseen(t):return tile_supply(board,t)-visible[t]>0
    if any(n>=4 or n>=3 and unseen(t) for t,n in counts.items()):return True
    return any(m.get("type")==1 and m.get("tiles") and
               (counts[tile_kind(m["tiles"][0])] or unseen(tile_kind(m["tiles"][0])))
               for m in own.get("melds",[]))
