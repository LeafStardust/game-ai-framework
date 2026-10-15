"""Guarded one-choice Pon and Chi buttons; ambiguous choice panels are unsupported."""

from dataclasses import dataclass
import time
from games.mahjong_soul.live.runtime.input import board_token


@dataclass(frozen=True)
class PonPlan:
    token: str
    connection: str
    step: int
    seat: int
    tile_kind: str
    tiles: tuple
    source_seat: int
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_pon(report, profile, *, now=None):
    if not report.get("state_ready"):
        raise ValueError("Reader is not ready")
    state = report["state"]
    operation = state.get("operations") or {}
    choices = [item for item in operation.get("operation_list", []) if item.get("type") == 3]
    if operation.get("seat") != state["seat"] or len(choices) != 1:
        raise ValueError("No own Pon operation")
    combinations = choices[0].get("combination", [])
    if len(combinations) != 1:
        raise ValueError("Pon choice panel requires explicit mapping")
    tiles = combinations[0].split("|")
    def kind(tile):
        return "5" + tile[1:] if tile.startswith("0") else tile
    if len(tiles) != 2 or kind(tiles[0]) != kind(tiles[1]):
        raise ValueError("Unsupported Pon combination")
    hand = list(state["hand"])
    for tile in tiles:
        if tile not in hand:
            raise ValueError("Pon contribution is missing from hand")
        hand.remove(tile)
    source = state["turn"]
    if (not isinstance(source, int) or not 0 <= source < state["player_count"] or source == state["seat"]
            or (report.get("last_event") or {}).get("name") != "ActionDiscardTile"):
        raise ValueError("Pon must follow a known opponent discard")
    river = state["discards"][source]
    if not river or river[-1].get("called") is not False or kind(river[-1]["tile"]) != kind(tiles[0]):
        raise ValueError("Pon source discard is uncertain or mismatched")
    expected_tiles = tuple(tiles + [river[-1]["tile"]])
    if (profile.get("version") != 1 or profile.get("verified") is not True
            or profile.get("operation_types") != [item.get("type") for item in operation["operation_list"]]):
        raise ValueError("Call-button layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = profile["pon"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid call-button coordinates")
    return PonPlan(board_token(report), report["game_connection"], state["step"], state["seat"],
                   kind(tiles[0]), expected_tiles, source, x, y, width, height,
                   (time.monotonic() if now is None else now) + 2)


class PonExecutor:
    def __init__(self, backend):
        self.backend = backend
        self.pending = None
        self.attempted = set()

    def execute(self, plan, report, *, enabled=False, now=None):
        if not enabled or self.pending is not None or plan.token in self.attempted:
            raise ValueError("Call input disabled, pending, or already attempted")
        if (time.monotonic() if now is None else now) >= plan.expires:
            raise ValueError("Call plan expired")
        if not report.get("state_ready") or board_token(report) != plan.token:
            raise ValueError("Board changed")
        self.attempted.add(plan.token)
        self.pending = plan
        self.backend.click(plan.x, plan.y, plan.width, plan.height)

    def observe(self, connection, event):
        from collections import Counter
        plan = self.pending
        data = event.get("data", {})
        tiles, origins = data.get("tiles", []), data.get("froms", [])
        if (not plan or connection != plan.connection or event.get("source") != "live"
                or event.get("name") != "ActionChiPengGang" or event.get("step", -1) <= plan.step
                or data.get("seat", 0) != plan.seat or data.get("type", 0) != 1
                or Counter(tiles) != Counter(plan.tiles) or len(origins) != 3):
            return False
        if Counter(zip(tiles, origins)) != Counter(zip(plan.tiles, (plan.seat, plan.seat, plan.source_seat))):
            return False
        self.pending = None
        return True


@dataclass(frozen=True)
class ChiPlan:
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


def plan_chi(report, profile, *, combination=None, visible_combinations=None, now=None):
    if not report.get("state_ready"):
        raise ValueError("Reader is not ready")
    state = report["state"]
    operation = state.get("operations") or {}
    choices = [item for item in operation.get("operation_list", []) if item.get("type") == 2]
    if operation.get("seat") != state["seat"] or len(choices) != 1:
        raise ValueError("No own Chi operation")
    combinations = choices[0].get("combination", [])
    multi = len(combinations) > 1
    if multi:
        if (combination not in combinations or profile.get("stage") != "chi_choices"
                or profile.get("combinations") != combinations or visible_combinations != combinations):
            raise ValueError("Chi choice panel requires verified visible combination order")
        points = profile.get("choice_points", [])
        if len(points) != len(combinations):
            raise ValueError("Chi choice coordinates do not match the panel")
        selected = combinations.index(combination)
    else:
        if len(combinations) != 1 or combination not in (None, combinations[0]):
            raise ValueError("No matching Chi combination")
        if profile.get("stage") == "chi_choices":
            raise ValueError("Choice panel profile cannot click a single-choice button")
        selected = 0
    source = state["turn"]
    if (state["player_count"] != 4 or source != (state["seat"] - 1) % 4
            or (report.get("last_event") or {}).get("name") != "ActionDiscardTile"):
        raise ValueError("Chi does not follow the previous seat's discard")
    river = state["discards"][source]
    if not river or river[-1].get("called") is not False:
        raise ValueError("Chi source discard is uncertain")
    own_tiles = combinations[selected].split("|")
    hand = list(state["hand"])
    if len(own_tiles) != 2:
        raise ValueError("Unsupported Chi combination")
    for tile in own_tiles:
        if tile not in hand:
            raise ValueError("Chi contribution is missing from hand")
        hand.remove(tile)
    tiles = own_tiles + [river[-1]["tile"]]
    kinds = ["5" + tile[1:] if tile.startswith("0") else tile for tile in tiles]
    if (any(len(tile) != 2 or tile[0] not in "123456789" or tile[1] not in "mps" for tile in kinds)
            or len({tile[1] for tile in kinds}) != 1):
        raise ValueError("Invalid Chi tile kinds")
    ranks = sorted(int(tile[0]) for tile in kinds)
    if ranks != list(range(ranks[0], ranks[0] + 3)):
        raise ValueError("Chi tiles are not a sequence")
    if (profile.get("version") != 1 or profile.get("verified") is not True
            or profile.get("operation_types") != [item.get("type") for item in operation["operation_list"]]):
        raise ValueError("Call-button layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = points[selected] if multi else profile["chi"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid call-button coordinates")
    return ChiPlan(board_token(report), report["game_connection"], state["step"], state["seat"],
                   source, tuple(tiles), x, y, width, height,
                   (time.monotonic() if now is None else now) + 2)


class ChiExecutor(PonExecutor):
    def observe(self, connection, event):
        from collections import Counter
        plan = self.pending
        data = event.get("data", {})
        tiles, origins = data.get("tiles", []), data.get("froms", [])
        if (not plan or connection != plan.connection or event.get("source") != "live"
                or event.get("name") != "ActionChiPengGang" or event.get("step", -1) <= plan.step
                or data.get("seat", 0) != plan.seat or data.get("type", 0) != 0
                or Counter(tiles) != Counter(plan.tiles) or len(origins) != 3):
            return False
        actual = Counter(zip(tiles, origins))
        expected = Counter(zip(plan.tiles, (plan.seat, plan.seat, plan.source_seat)))
        if actual != expected:
            return False
        self.pending = None
        return True
