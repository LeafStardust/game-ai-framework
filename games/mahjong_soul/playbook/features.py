"""Visible-state value and defense facts shared by strategy playbooks."""
from collections import Counter
from games.mahjong_soul.live.runtime.kan import tile_kind


def dora_kind(indicator, player_count):
    tile = tile_kind(indicator); rank = int(tile[0]); suit = tile[1]
    if player_count == 3 and suit == "m":
        if rank not in (1,9): raise ValueError("Removed sanma dora indicator")
        return "9m" if rank == 1 else "1m"
    if suit != "z": return str(rank%9+1)+suit
    if rank <= 4: return str(rank%4+1)+"z"
    return str(5+(rank-4)%3)+"z"


def value_honors(board):
    meta = board["round"]; count = board["player_count"]
    dealer = meta.get("ju"); wind = meta.get("chang")
    if type(dealer) is not int or not 0 <= dealer < count or type(wind) is not int or not 0 <= wind <= 3:
        raise ValueError("Round/seat wind is unknown")
    honors = Counter({"5z":1,"6z":1,"7z":1})
    honors[str((board["self_seat"]-dealer)%count+1)+"z"] += 1
    honors[str(wind+1)+"z"] += 1
    return honors


def riichi_threats(board):
    return [p for p in board["players"] if not p["is_self"] and p["riichi"] in ("declared","accepted")]


def safe_against(tile, threats):
    kind = tile_kind(tile)
    return [p["seat"] for p in threats
            if any(tile_kind(d["tile"]) == kind for d in p["discards"])]


def discard_features(board, tile):
    own = next(p for p in board["players"] if p["is_self"])
    hand = list(board["self"]["hand"]); before = Counter(tile_kind(t) for t in hand)
    hand.remove(tile); after = Counter(tile_kind(t) for t in hand)
    honors = value_honors(board); kind = tile_kind(tile)
    dora = Counter(dora_kind(t,board["player_count"]) for t in board["dora_indicators"])
    fixed = Counter(tile_kind(t) for m in own["melds"] for t in m["tiles"])
    # Structural evidence only; not a full hand value or yaku calculator.
    yakuhai = [t for t in honors if after[t] >= 3 or fixed[t] >= 3]
    return {"dora_loss":dora[kind]+int(tile.startswith("0")),
            "yakuhai_pair_loss":honors[kind] if before[kind] >= 2 and after[kind] < 2 else 0,
            "yakuhai_triplet_loss":honors[kind] if before[kind] >= 3 and after[kind] < 3 else 0,
            "yakuhai_triplets":yakuhai,
            "safe_against_riichi_seats":safe_against(tile,riichi_threats(board))}
