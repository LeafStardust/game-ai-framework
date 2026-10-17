"""Deterministic shanten/visible-ukeire discard policy; no defensive model."""
from copy import deepcopy
from functools import lru_cache

from mahjong.shanten import Shanten
from agents.mahjong_soul.policy import BaselinePolicy
from games.mahjong_soul.live.runtime.kan import tile_kind

KINDS = tuple(str(n)+s for s in "mps" for n in range(1,10))+tuple(str(n)+"z" for n in range(1,8))
INDEX = {tile:i for i,tile in enumerate(KINDS)}


def counts34(tiles):
    counts = [0]*34
    for tile in tiles:
        counts[INDEX[tile_kind(tile)]] += 1
    if max(counts) > 4: raise ValueError("More than four copies of a tile")
    return tuple(counts)


@lru_cache(maxsize=50000)
def shanten(counts, meld_count=0):
    if (type(meld_count) is not int or not 0 <= meld_count <= 4 or len(counts) != 34
            or any(type(c) is not int or not 0 <= c <= 4 for c in counts)
            or sum(counts) not in (13-3*meld_count,14-3*meld_count)):
        raise ValueError("Concealed tile count does not match meld count")
    # The library infers fixed melds from the concealed hand's reduced length.
    # Seven pairs and thirteen orphans are only possible with no fixed melds.
    return Shanten.calculate_shanten(counts, use_chiitoitsu=meld_count == 0,
                                     use_kokushi=meld_count == 0)


def rank_discards(request):
    board = request["observation"]["board"]
    if not board.get("visibility_complete"): raise ValueError("Visible counts are incomplete")
    players = board["players"]
    own = [p for p in players if p["seat"] == board["self_seat"] and p["is_self"]]
    if len(own) != 1: raise ValueError("Own melds are unknown")
    melds = own[0]["melds"]
    for meld in melds:
        code = meld.get("type"); tiles = meld.get("tiles", [])
        if code not in (0,1,2,3) or len(tiles) != (3 if code in (0,1) else 4):
            raise ValueError("Unsupported fixed meld")
        counts34(tiles)
    fixed = len(melds)
    hand = board["self"]["hand"]; counts = counts34(hand)
    if len(hand) != 14-3*fixed: raise ValueError("Not a discard-stage hand")
    pool = [4]*34
    if board["player_count"] == 3:
        for i in range(1,8): pool[i] = 0
    elif board["player_count"] != 4: raise ValueError("Unsupported player count")
    visible = [0]*34
    for tile, count in board["visible_tile_counts"].items():
        if type(count) is not int or count < 0: raise ValueError("Invalid visible count")
        visible[INDEX[tile_kind(tile)]] += count
    if any(visible[i] < counts[i] or visible[i] > pool[i] for i in range(34)):
        raise ValueError("Visible counts do not cover own hand or exceed tile pool")
    own_tiles = counts34(hand+[t for meld in melds for t in meld["tiles"]])
    if any(visible[i] < own_tiles[i] for i in range(34)):
        raise ValueError("Visible counts omit fixed own melds")
    result = []
    for action in request["actions"]:
        if action["kind"] != "discard": continue
        tile = action["tile"]; index = INDEX[tile_kind(tile)]
        if tile not in hand: raise ValueError("Offered discard is not in hand")
        after = list(counts); after[index] -= 1
        distance = shanten(tuple(after), fixed)
        improvements = []
        for draw in range(34):
            # The discarded tile remains visible; do not add it back to availability.
            remaining = pool[draw]-visible[draw]
            if remaining <= 0 or after[draw] >= 4: continue
            after[draw] += 1
            better = shanten(tuple(after), fixed) < distance
            after[draw] -= 1
            if better: improvements.append({"tile":KINDS[draw],"unseen":remaining})
        result.append({"action":deepcopy(action),"shanten":distance,
                       "ukeire":sum(t["unseen"] for t in improvements),
                       "improving_tiles":improvements})
    drawn = board["self"].get("drawn_tile")
    result.sort(key=lambda r:(r["shanten"],-r["ukeire"],r["action"]["tile"].startswith("0"),
                              r["action"]["tile"] != drawn, r["action"]["tile"]))
    return result


class EfficiencyPolicy(BaselinePolicy):
    """Minimize shanten, maximize unseen improving copies, then retain red fives.

    Still accepts offered wins and declines calls; no Riichi, value, yaku or
    opponent-danger assessment is introduced by this discard heuristic.
    """
    def __init__(self):
        self.last_analysis = None

    def choose(self, request):
        self.last_analysis = None
        if any(a["kind"] in ("tsumo","ron") for a in request["actions"]):
            return super().choose(request)
        if any(a["kind"] == "discard" for a in request["actions"]):
            ranked = rank_discards(request)
            best = ranked[0]
            self.last_analysis = {"board_token":request["board_token"],
                                  "shanten":best["shanten"],"ukeire":best["ukeire"],
                                  "improving_tiles":deepcopy(best["improving_tiles"])}
            return deepcopy(best["action"])
        return super().choose(request)
