"""Read-only decision requests and server-offer validation. No policy or input."""
from collections import Counter
from copy import deepcopy
import math
import json
import time
import uuid

from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.kan import tile_kind
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot

NAMES = {1:"discard", 2:"chi", 3:"pon", 4:"closed_kan", 5:"open_kan",
         6:"added_kan", 7:"riichi", 8:"tsumo", 9:"ron"}


def _source(report):
    state = report["state"]; source = state.get("turn")
    if (type(source) is not int or not 0 <= source < state["player_count"]
            or source == state["seat"]
            or (report.get("last_event") or {}).get("name") != "ActionDiscardTile"):
        raise ValueError("Opponent discard source is unknown")
    river = state["discards"][source]
    if not river or river[-1].get("called") is not False:
        raise ValueError("Source discard is already called or unknown")
    tile = river[-1]["tile"]; tile_kind(tile)
    return source, tile



def ron_source(report):
    state=report.get("state") or {}
    if (report.get("last_event") or {}).get("name")!="ActionAnGangAddGang":return _source(report)
    source=state.get("win_source") or {}
    if (source.get("event")!="ActionAnGangAddGang" or source.get("step")!=state.get("step")
            or type(source.get("seat")) is not int or source["seat"] not in range(state["player_count"])
            or source["seat"]!=state.get("turn") or source["seat"]==state.get("seat")):
        raise ValueError("Robbed Kan source is unverified")
    tile=source.get("tile");tile_kind(tile)
    return source["seat"],tile

def offered_actions(report):
    """Normalize supported server offers, independent of mouse/UI support.

    Unknown codes are rejected rather than guessed. Exact server combination
    strings and red-five identity are retained; these are intents, not click plans.
    """
    state = report.get("state") or {}
    if not report.get("state_ready") or not report.get("connection_open"):
        raise ValueError("A ready open game connection is required")
    operation = state.get("operations") or {}
    offers = operation.get("operation_list", [])
    if operation.get("seat") != state.get("seat") or not offers:
        raise ValueError("No own decision offer")
    if not isinstance(offers, list) or any(not isinstance(o, dict) for o in offers):
        raise ValueError("Malformed operation list")
    types = [o.get("type") for o in offers]
    if any(type(t) is not int or t not in NAMES for t in types) or len(set(types)) != len(types):
        raise ValueError("Unsupported or duplicate operation codes")
    hand = state.get("hand", [])
    for tile in hand: tile_kind(tile)
    actions = []
    for offer in offers:
        code = offer["type"]; kind = NAMES[code]
        combinations = offer.get("combination", [])
        if not isinstance(combinations, list) or any(not isinstance(c, str) for c in combinations):
            raise ValueError("Malformed combinations")
        if code == 1:
            forbidden = {tile_kind(t) for t in combinations}
            own_riichi=state.get("riichi",[])
            locked=(len(own_riichi)>state["seat"] and own_riichi[state["seat"]] in ("declared","accepted"))
            pool=[state.get("drawn_tile")] if locked else sorted(set(hand))
            if locked and pool[0] not in hand:raise ValueError("Riichi draw is unknown")
            actions.extend({"kind":kind,"tile":t} for t in pool if tile_kind(t) not in forbidden)
        elif code == 7:
            if 1 not in types:
                raise ValueError("Riichi requires a discard offer")
            # Offer ordering does not determine whether discard is available.
            restrictions = next(o for o in offers if o["type"] == 1).get("combination", [])
            forbidden = {tile_kind(t) for t in restrictions}
            for tile in combinations:
                tile_kind(tile)
                if tile not in hand or tile_kind(tile) in forbidden:
                    raise ValueError("Riichi tile is missing or forbidden")
                actions.append({"kind":kind,"tile":tile})
        elif code in (8, 9):
            if combinations:
                raise ValueError("Unsupported win combination encoding")
            if code == 8:
                tile = state.get("drawn_tile")
                if tile not in hand: raise ValueError("Winning draw is unknown")
                actions.append({"kind":kind,"tile":tile})
            else:
                source, tile = ron_source(report)
                actions.append({"kind":kind,"tile":tile,"source_seat":source})
        else:
            if not combinations: raise ValueError("Call has no combination")
            for combination in combinations:
                tiles = combination.split("|")
                kinds = [tile_kind(t) for t in tiles]
                count = {2:2,3:2,4:4,5:3,6:4}[code]
                if len(tiles) != count: raise ValueError("Invalid call contribution length")
                if code != 2 and len(set(kinds)) != 1:
                    raise ValueError("Call tiles do not share a kind")
                action = {"kind":kind,"combination":combination}
                if code == 6:
                    pons = [m for m in state["melds"][state["seat"]]
                            if m.get("type") == 1 and len(m.get("tiles", [])) == 3
                            and all(tile_kind(t) == kinds[0] for t in m["tiles"])]
                    if len(pons) != 1: raise ValueError("Added kan has no unique matching Pon")
                    extra = Counter(tiles)-Counter(pons[0]["tiles"])
                    if (Counter(pons[0]["tiles"])-Counter(tiles) or sum(extra.values()) != 1
                            or next(extra.elements()) not in hand):
                        raise ValueError("Added-kan exact tile is missing")
                elif Counter(tiles)-Counter(hand):
                    raise ValueError("Call contributions are missing from hand")
                if code in (2,3,5):
                    source, called = _source(report)
                    if code == 2:
                        ranks = sorted(int(tile_kind(t)[0]) for t in tiles+[called])
                        suits = {t[1] for t in tiles+[called]}
                        if (source != (state["seat"]-1)%state["player_count"]
                                or len(suits) != 1 or "z" in suits
                                or ranks != list(range(ranks[0], ranks[0]+3))):
                            raise ValueError("Chi source or sequence is invalid")
                    elif tile_kind(called) != kinds[0]:
                        raise ValueError("Call source tile differs")
                    action.update(source_seat=source, called_tile=called)
                actions.append(action)
    if all(t in (2,3,5,9) for t in types):
        actions.append({"kind":"skip"})
    unique = []
    for action in actions:
        if action not in unique: unique.append(action)
    if not unique:
        raise ValueError("No supported action remains in this offer")
    return unique


def decision_request(report, *, now=None, ttl=2.0):
    now = time.monotonic() if now is None else now
    if (type(ttl) not in (int,float) or not math.isfinite(ttl) or ttl <= 0
            or type(now) not in (int,float) or not math.isfinite(now) or not math.isfinite(now+ttl)):
        raise ValueError("Decision timing must be finite and positive")
    actions = offered_actions(report)
    return {"version":1,"request_id":uuid.uuid4().hex,"board_token":board_token(report),
            "issued_at":now,"expires_at":now+ttl,
            "observation":observation_from_snapshot(report),"actions":actions}


def validate_proposal(request, proposal, report, *, now=None):
    """Validate an intent against a fresh snapshot; return no executable coordinates.

    Callers must independently establish capture freshness. Monotonic timestamps
    belong to this process/boot and must not be persisted as reusable requests.
    """
    now = time.monotonic() if now is None else now
    if (type(now) not in (int,float) or not math.isfinite(now)
            or not request["issued_at"] <= now < request["expires_at"]):
        raise ValueError("Decision request expired or clock is invalid")
    if (not isinstance(proposal, dict) or set(proposal) != {"version","request_id","board_token","action"}
            or type(proposal["version"]) is not int or proposal["version"] != 1
            or request.get("version") != 1 or proposal["request_id"] != request["request_id"]
            or proposal["board_token"] != request["board_token"]
            or board_token(report) != request["board_token"]):
        raise ValueError("Proposal does not match the current request and board")
    action = proposal["action"]
    if (not isinstance(action, dict) or json.dumps(action, sort_keys=True) not in
            [json.dumps(a, sort_keys=True) for a in offered_actions(report)]):
        raise ValueError("Action is not offered on the current board")
    return {"version":1,"request_id":request["request_id"],"board_token":request["board_token"],
            "action":deepcopy(action),"executable":False}
