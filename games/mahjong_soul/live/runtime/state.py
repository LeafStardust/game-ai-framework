"""Conservative visible-state tracker for ordinary three/four-player matches."""

from copy import deepcopy


class GameState:
    def __init__(self, seat=None):
        self.seat = seat
        self.last_step = None
        self.status = "waiting_for_round"
        self.issues = []
        self.hand = []
        self.discards = [[], [], [], []]
        self.melds = [[], [], [], []]
        self.norths = [0, 0, 0, 0]
        self.scores = []
        self.doras = []
        self.operations = None
        self.round = {}
        self.left_tile_count = None
        self.turn = None

    def invalidate(self, reason):
        self.status = "incomplete"
        if reason not in self.issues:
            self.issues.append(reason)
        self.operations = None

    def _remove(self, tile):
        if tile not in self.hand:
            self.invalidate(f"Own hand missing tile: {tile}")
        else:
            self.hand.remove(tile)

    def apply(self, event):
        name, data, step = event["name"], event["data"], event["step"]
        if name == "ActionNewRound":
            seat = self.seat
            self.__init__(seat)
            self.status = "tracking" if seat is not None else "incomplete"
            if seat is None:
                self.issues.append("Own seat is unknown")
            self.hand = list(data.get("tiles", []))
            self.round = {key: data.get(key, 0) for key in ("chang", "ju", "ben", "liqibang")}
        else:
            if self.last_step is None:
                self.invalidate("Capture started after round start")
            elif step <= self.last_step:
                return False
            elif step != self.last_step + 1:
                self.invalidate(f"Action gap: {self.last_step} -> {step}")
        self.last_step = step
        seat = data.get("seat", 0)
        if not isinstance(seat, int) or not 0 <= seat < 4:
            self.invalidate("Invalid event seat")
            return False
        self.operations = deepcopy(data.get("operation"))
        if data.get("doras"):
            self.doras = list(data["doras"])
        elif data.get("dora"):
            self.doras = [data["dora"]]
        if "left_tile_count" in data:
            self.left_tile_count = data["left_tile_count"]
        if data.get("scores"):
            self.scores = list(data["scores"])
        liqi = data.get("liqi")
        if liqi and self.scores:
            liqi_seat = liqi.get("seat", 0)
            if 0 <= liqi_seat < len(self.scores):
                self.scores[liqi_seat] = liqi.get("score", 0)
        if name == "ActionDealTile":
            self.turn = seat
            if seat == self.seat:
                tile = data.get("tile", "")
                if tile:
                    self.hand.append(tile)
                else:
                    self.invalidate("Own draw tile is missing")
        elif name == "ActionDiscardTile":
            tile = data.get("tile", "")
            if not tile:
                self.invalidate("Discard tile is missing")
            self.discards[seat].append({"tile": tile, "riichi": data.get("is_liqi", False),
                                       "tsumogiri": data.get("moqie", False)})
            if seat == self.seat:
                self._remove(tile)
            self.turn = seat
        elif name == "ActionChiPengGang":
            self.melds[seat].append(deepcopy(data))
            tiles, froms = data.get("tiles", []), data.get("froms", [])
            if len(tiles) != len(froms):
                self.invalidate("Meld tile origins are missing")
            elif seat == self.seat:
                for tile, origin in zip(tiles, froms):
                    if origin == seat:
                        self._remove(tile)
            self.turn = seat
        elif name == "ActionBaBei":
            self.norths[seat] += 1
            if seat == self.seat:
                self._remove("4z")
        elif name == "ActionAnGangAddGang":
            self.melds[seat].append(deepcopy(data))
            self.invalidate("Concealed/added kan state reduction is pending")
        elif name in ("ActionHule", "ActionNoTile", "ActionLiuJu"):
            end = data.get("gameend", {})
            if end.get("scores"):
                self.scores = list(end["scores"])
            if self.status != "incomplete":
                self.status = "round_ended"
            self.operations = None
        elif name != "ActionNewRound":
            self.invalidate(f"Unsupported action: {name}")
        return True

    def snapshot(self):
        return deepcopy({"status": self.status, "issues": self.issues, "seat": self.seat,
                         "step": self.last_step, "round": self.round, "hand": self.hand,
                         "discards": self.discards, "melds": self.melds, "norths": self.norths,
                         "scores": self.scores, "doras": self.doras,
                         "left_tile_count": self.left_tile_count, "turn": self.turn,
                         "operations": self.operations})
