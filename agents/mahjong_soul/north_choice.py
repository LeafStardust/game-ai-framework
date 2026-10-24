"""Compare Kita with retained-hand shape; no speculative replacement draw credit."""
from agents.mahjong_soul.efficiency import rank_discards
from agents.mahjong_soul.yakuman import yakuman_targets


def north_choice(request):
    board=request["observation"]["board"]
    hand=board["self"]["hand"]
    if "4z" not in hand:
        return {"extract":False,"reason":"no_north"}
    targets=yakuman_targets(board,hand)
    if any(t["target_route"] in ("yakuman_kokushi","yakuman_all_honors") for t in targets):
        return {"extract":False,"reason":"qualified_north_yakuman"}
    # Treat extraction as discarding North for the immediate shape comparison.
    # Kita then banks a bonus and provides an extra draw, unlike that discard.
    probe=dict(request,actions=[{"kind":"discard","tile":t} for t in sorted(set(hand))])
    ranked=rank_discards(probe)
    best=ranked[0]
    north=next(o for o in ranked if o["action"]["tile"]=="4z")
    pair=hand.count("4z")>=2
    allowed=(north["shanten"]==best["shanten"] and
             (not pair or north["ukeire"]>=best["ukeire"]))
    return {"extract":allowed,"reason":"bank_kita_without_shape_loss" if allowed else "retain_useful_north",
            "north_shanten":north["shanten"],"north_ukeire":north["ukeire"],
            "best_shanten":best["shanten"],"best_ukeire":best["ukeire"]}
