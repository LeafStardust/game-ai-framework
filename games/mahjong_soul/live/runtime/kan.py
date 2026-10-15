"""Guarded single-choice concealed and open kan; added kan is unsupported."""

from dataclasses import dataclass
from collections import Counter
import time

from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.calls import PonExecutor


def tile_kind(tile):
    if not isinstance(tile, str) or len(tile) != 2:
        raise ValueError("Invalid kan tile")
    rank, suit = tile
    if not ((suit in "mps" and rank in "0123456789") or (suit == "z" and rank in "1234567")):
        raise ValueError("Invalid kan tile")
    return "5" + suit if rank == "0" else tile


@dataclass(frozen=True)
class ConcealedKanPlan:
    token: str
    connection: str
    step: int
    seat: int
    tile_kind: str
    contributed_tiles: tuple
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_concealed_kan(report, profile, *, now=None):
    state = report.get("state") or {}
    operation = state.get("operations") or {}
    choices = [item for item in operation.get("operation_list", []) if item.get("type") == 4]
    if not report.get("state_ready") or operation.get("seat") != state.get("seat") or len(choices) != 1:
        raise ValueError("No own concealed-kan operation")
    combinations = choices[0].get("combination", [])
    if len(combinations) != 1:
        raise ValueError("Kan choice panel requires explicit mapping")
    tiles = combinations[0].split("|")
    if len(tiles) != 4 or len({tile_kind(tile) for tile in tiles}) != 1:
        raise ValueError("Invalid concealed-kan combination")
    if Counter(tiles) - Counter(state["hand"]):
        raise ValueError("Kan contribution is missing from the own hand")
    if (profile.get("version") != 1 or profile.get("verified") is not True
            or profile.get("stage") != "call_offer"
            or profile.get("operation_types") != [item.get("type") for item in operation["operation_list"]]):
        raise ValueError("Kan layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = profile["kan"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid kan coordinates")
    return ConcealedKanPlan(board_token(report), report["game_connection"], state["step"], state["seat"],
                            tile_kind(tiles[0]), tuple(tiles), x, y, width, height,
                            (time.monotonic() if now is None else now) + 2)


class ConcealedKanExecutor(PonExecutor):
    def observe(self, connection, event):
        plan = self.pending
        data = event.get("data", {})
        if (not plan or connection != plan.connection or event.get("source") != "live"
                or event.get("name") != "ActionAnGangAddGang" or event.get("step", -1) <= plan.step
                or data.get("seat", 0) != plan.seat or data.get("type", 0) != 3):
            return False
        try:
            kind = tile_kind(data.get("tiles"))
        except ValueError:
            return False
        if kind != plan.tile_kind:
            return False
        self.pending = None
        return True


@dataclass(frozen=True)
class OpenKanPlan:
    token: str
    connection: str
    step: int
    seat: int
    source_seat: int
    tiles: tuple
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_open_kan(report, profile, *, now=None):
    state = report.get("state") or {}
    operation = state.get("operations") or {}
    choices = [item for item in operation.get("operation_list", []) if item.get("type") == 5]
    if not report.get("state_ready") or operation.get("seat") != state.get("seat") or len(choices) != 1:
        raise ValueError("No own open-kan operation")
    combinations = choices[0].get("combination", [])
    if len(combinations) != 1:
        raise ValueError("Kan choice panel requires explicit mapping")
    tiles = combinations[0].split("|")
    if len(tiles) != 3 or len({tile_kind(tile) for tile in tiles}) != 1:
        raise ValueError("Invalid open-kan contribution")
    if Counter(tiles) - Counter(state["hand"]):
        raise ValueError("Open-kan contribution is missing from hand")
    source = state.get("turn")
    if (not isinstance(source, int) or not 0 <= source < state["player_count"] or source == state["seat"]
            or (report.get("last_event") or {}).get("name") != "ActionDiscardTile"):
        raise ValueError("Open kan requires a known opponent discard")
    river = state["discards"][source]
    if not river or river[-1].get("called") is not False or tile_kind(river[-1]["tile"]) != tile_kind(tiles[0]):
        raise ValueError("Open-kan source discard is uncertain or mismatched")
    tiles.append(river[-1]["tile"])
    if (profile.get("version") != 1 or profile.get("verified") is not True
            or profile.get("stage") != "call_offer"
            or profile.get("operation_types") != [item.get("type") for item in operation["operation_list"]]):
        raise ValueError("Kan layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = profile["kan"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid kan coordinates")
    return OpenKanPlan(board_token(report), report["game_connection"], state["step"], state["seat"],
                       source, tuple(tiles), x, y, width, height,
                       (time.monotonic() if now is None else now) + 2)


class OpenKanExecutor(PonExecutor):
    def observe(self, connection, event):
        plan = self.pending
        data = event.get("data", {})
        tiles, origins = data.get("tiles", []), data.get("froms", [])
        if (not plan or connection != plan.connection or event.get("source") != "live"
                or event.get("name") != "ActionChiPengGang" or event.get("step", -1) <= plan.step
                or data.get("seat", 0) != plan.seat or data.get("type", 0) != 2
                or Counter(tiles) != Counter(plan.tiles) or len(origins) != 4):
            return False
        if Counter(zip(tiles, origins)) != Counter(zip(plan.tiles, (plan.seat, plan.seat, plan.seat, plan.source_seat))):
            return False
        self.pending = None
        return True
