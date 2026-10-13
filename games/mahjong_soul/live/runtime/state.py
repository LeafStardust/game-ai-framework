"""Conservative visible-state tracker for ordinary three/four-player matches."""

from copy import deepcopy


class GameState:
    def __init__(self, seat=None, player_count=4):
        if player_count not in (3, 4):
            raise ValueError("Only three/four-player matches are supported")
        self.player_count = player_count
        self.seat = seat
        self.last_step = None
        self.status = "waiting_for_round"
        self.issues = []
        self.hand = []
        self.discards = [[] for _ in range(player_count)]
        self.melds = [[] for _ in range(player_count)]
        self.norths = [0] * player_count
        self.scores = []
        self.doras = []
        self.operations = None
        self.round = {}
        self.left_tile_count = None
        self.turn = None
        self._last_event = None
        self._awaiting_step = False
        self.player_metadata = []

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

    @staticmethod
    def _tile_kind(tile):
        return "5" + tile[1:] if len(tile) == 2 and tile[0] == "0" else tile

    def _kan(self, seat, data):
        tile, kind = data.get("tiles", ""), data.get("type")
        if not isinstance(tile, str) or len(tile) != 2:
            self.invalidate("Kan tile is missing or malformed")
            return
        normalized = self._tile_kind(tile)
        if kind == 3:  # Concealed kan: all four come from the declarer's hand.
            removed = []
            if seat == self.seat:
                removed = [item for item in self.hand if self._tile_kind(item) == normalized]
                if len(removed) != 4:
                    self.invalidate("Own concealed kan does not match four hand tiles")
                    return
                for item in removed:
                    self._remove(item)
            self.melds[seat].append({"type": 3, "tiles": removed or [tile] * 4,
                                     "froms": [seat] * 4, "raw": deepcopy(data)})
        elif kind == 2:  # Added kan upgrades an existing pon, not a new meld.
            pon = next((meld for meld in self.melds[seat]
                        if meld.get("type") == 1 and len(meld.get("tiles", [])) == 3
                        and all(self._tile_kind(item) == normalized for item in meld["tiles"])), None)
            if pon is None:
                self.invalidate("Added kan has no matching pon")
                return
            added = tile
            if seat == self.seat:
                matches = [item for item in self.hand if self._tile_kind(item) == normalized]
                if not matches:
                    self.invalidate("Own added kan tile is missing")
                    return
                added = tile if tile in matches else matches[0]
                self._remove(added)
            pon["type"] = 2
            pon["tiles"].append(added)
            pon.setdefault("froms", []).append(seat)
            pon["added_kan"] = deepcopy(data)
        else:
            self.invalidate(f"Unsupported kan type: {kind}")

    def restore(self, snapshot, next_step=None):
        """Replace state from GameSnapshot before applying its following actions."""
        seat = self.seat
        players = snapshot.get("players", [])
        self.__init__(seat, len(players) if len(players) in (3, 4) else self.player_count)
        self.status = "tracking"
        if seat is None:
            self.invalidate("Own seat is unknown")
        self.round = {key: snapshot.get(key, 0) for key in ("chang", "ju", "ben", "liqibang")}
        self.hand = list(snapshot.get("hands", []))
        self.doras = list(snapshot.get("doras", []))
        self.left_tile_count = snapshot.get("left_tile_count")
        self.turn = snapshot.get("index_player")
        players = snapshot.get("players", [])
        if len(players) not in (3, 4):
            self.invalidate("Snapshot player list is incomplete")
        if seat is not None and seat >= len(players):
            self.invalidate("Own seat is outside snapshot player list")
        self.scores = [player.get("score", 0) for player in players]
        self.player_metadata = [{"riichi_position": player.get("liqiposition"),
                                 "concealed_tile_count": player.get("tilenum")} for player in players]
        for index, player in enumerate(players[:self.player_count]):
            for tile in player.get("qipais", []):
                # The snapshot does not carry live moqie/is_liqi booleans.
                self.discards[index].append({"tile": tile, "riichi": None, "tsumogiri": None})
                if len(tile) != 2:
                    self.invalidate("Snapshot discard uses an unsupported annotation")
            for meld in player.get("mings", []):
                kind = meld.get("type", 0)
                if kind not in (0, 1, 2, 3):
                    self.invalidate(f"Unsupported snapshot meld type: {kind}")
                self.melds[index].append({"type": kind, "tiles": list(meld.get("tile", [])),
                                         "froms": list(meld.get("from", []))})
        self.last_step = next_step - 1 if next_step is not None else None
        self._awaiting_step = next_step is None

    def apply(self, event):
        name, data, step = event["name"], event["data"], event["step"]
        identity = (name, step, data)
        if identity == self._last_event:
            return False
        if name == "ActionMJStart":
            self.__init__(self.seat, self.player_count)
            self.last_step = step
            self._last_event = deepcopy(identity)
            return True
        if name == "ActionNewRound":
            seat = self.seat
            scores = data.get("scores", [])
            self.__init__(seat, len(scores) if len(scores) in (3, 4) else self.player_count)
            self.status = "tracking" if seat is not None else "incomplete"
            if seat is None:
                self.issues.append("Own seat is unknown")
            self.hand = list(data.get("tiles", []))
            self.round = {key: data.get(key, 0) for key in ("chang", "ju", "ben", "liqibang")}
        else:
            if self._awaiting_step:
                self._awaiting_step = False
            elif self.last_step is None:
                self.invalidate("Capture started after round start")
            elif step <= self.last_step:
                return False
            elif step != self.last_step + 1:
                self.invalidate(f"Action gap: {self.last_step} -> {step}")
        self.last_step = step
        self._last_event = deepcopy(identity)
        seat = data.get("seat", 0)
        if not isinstance(seat, int) or not 0 <= seat < self.player_count:
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
        if liqi and not liqi.get("failed", False) and self.scores:
            liqi_seat = liqi.get("seat", 0)
            if 0 <= liqi_seat < len(self.scores):
                self.scores[liqi_seat] = liqi.get("score", 0)
            if "liqibang" in liqi:
                self.round["liqibang"] = liqi["liqibang"]
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
            self._kan(seat, data)
            self.turn = seat
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
        return deepcopy({"player_count": self.player_count, "status": self.status, "issues": self.issues, "seat": self.seat,
                         "step": self.last_step, "round": self.round, "hand": self.hand,
                         "discards": self.discards, "melds": self.melds, "norths": self.norths,
                         "scores": self.scores, "doras": self.doras,
                         "left_tile_count": self.left_tile_count, "turn": self.turn,
                         "operations": self.operations, "player_metadata": self.player_metadata})
