"""Conservative visible-state tracker for ordinary three/four-player matches."""

from copy import deepcopy
from collections import Counter
from games.mahjong_soul.live.runtime.scoring_context import ScoringContext


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
        self.opening_hand = []
        self.scoring_context = ScoringContext(seat)
        self.discards = [[] for _ in range(player_count)]
        self.melds = [[] for _ in range(player_count)]
        self.norths = [0] * player_count
        self.riichi = ["none"] * player_count
        self.drawn_tile = None
        self.win_source = None
        self.furiten = None
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
        self.scoring_context=ScoringContext(self.seat)
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
            self.melds[seat].append({"type": 3, "tiles": removed or [normalized] * 4,
                                     "froms": [seat] * 4, "red_fives_known": seat == self.seat, "raw": deepcopy(data)})
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

    def _mark_called_discard(self, seat, tiles, froms):
        called = [(tile, origin) for tile, origin in zip(tiles, froms) if origin != seat]
        if len(called) != 1:
            self.invalidate("Meld does not identify exactly one called discard")
            return
        tile, origin = called[0]
        if not isinstance(origin, int) or not 0 <= origin < self.player_count:
            self.invalidate("Called discard has an invalid source seat")
            return
        river = self.discards[origin]
        if not river or river[-1]["tile"] != tile or river[-1].get("called"):
            self.invalidate("Called tile does not match the source's last discard")
            return
        river[-1]["called"] = True

    def _settle_scores(self, data, name):
        scores = data.get("scores", [])
        if scores and all(isinstance(score, int) for score in scores):
            self.scores = list(scores)
        elif name == "ActionNoTile" and scores:
            # The usual exhaustive draw has one old-score/delta vector. Multiple
            # nagashi settlements need a live example before their order is trusted.
            if len(scores) != 1 or not isinstance(scores[0], dict):
                self.invalidate("Multiple exhaustive-draw settlements need verification")
                return
            old = scores[0].get("old_scores", [])
            delta = scores[0].get("delta_scores", []) or [0] * self.player_count
            if len(old) != self.player_count or len(delta) != self.player_count:
                self.invalidate("Exhaustive-draw score vectors are incomplete")
                return
            self.scores = [before + change for before, change in zip(old, delta)]
        end = data.get("gameend")
        if isinstance(end, dict) and end.get("scores"):
            self.scores = list(end["scores"])
        if self.scores and (len(self.scores) != self.player_count or not all(isinstance(score, int) for score in self.scores)):
            self.invalidate("Scores do not match the player count")

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
        self.riichi = ["unknown"] * self.player_count
        self.player_metadata = [{"riichi_position": player.get("liqiposition"),
                                 "concealed_tile_count": player.get("tilenum")} for player in players]
        for index, player in enumerate(players[:self.player_count]):
            for tile in player.get("qipais", []):
                # The snapshot does not carry live moqie/is_liqi booleans.
                self.discards[index].append({"tile": tile, "riichi": None, "tsumogiri": None, "called": None})
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
            self.opening_hand = list(self.hand)
            if len(self.hand)==14 and self.seat==data.get("ju",0):self.drawn_tile=self.hand[-1]
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
        self.scoring_context.observe(name,data,self.discards,self.melds,self.left_tile_count,self.round,self.hand)
        self.last_step = step
        self._last_event = deepcopy(identity)
        seat = data.get("seat", 0)
        if not isinstance(seat, int) or not 0 <= seat < self.player_count:
            self.invalidate("Invalid event seat")
            return False
        self.win_source=None
        if seat!=self.seat and name=="ActionAnGangAddGang":
            self.win_source={"seat":seat,"tile":data.get("tiles"),"step":step,"event":name}
        self.operations = deepcopy(data.get("operation"))
        if data.get("doras"):
            self.doras = list(data["doras"])
        elif data.get("dora"):
            self.doras = [data["dora"]]
        if "left_tile_count" in data:
            self.left_tile_count = data["left_tile_count"]
        self._settle_scores(data, name)
        if "zhenting" in data:
            self.furiten = data["zhenting"]
        liqi = data.get("liqi")
        if liqi and liqi.get("failed", False):
            liqi_seat = liqi.get("seat", 0)
            if 0 <= liqi_seat < self.player_count:
                self.riichi[liqi_seat] = "none"
        if liqi and not liqi.get("failed", False) and self.scores:
            liqi_seat = liqi.get("seat", 0)
            if 0 <= liqi_seat < len(self.scores):
                self.scores[liqi_seat] = liqi.get("score", 0)
                self.riichi[liqi_seat] = "accepted"
            if "liqibang" in liqi:
                self.round["liqibang"] = liqi["liqibang"]
        if name == "ActionDealTile":
            self.turn = seat
            if seat == self.seat:
                tile = data.get("tile", "")
                if tile:
                    self.hand.append(tile)
                    self.drawn_tile = tile
                else:
                    self.invalidate("Own draw tile is missing")
        elif name == "ActionDiscardTile":
            tile = data.get("tile", "")
            if not tile:
                self.invalidate("Discard tile is missing")
            self.discards[seat].append({"tile": tile, "riichi": data.get("is_liqi", False),
                                       "tsumogiri": data.get("moqie", False), "called": False})
            if data.get("is_liqi", False):
                self.riichi[seat] = "declared"
            if seat == self.seat:
                self._remove(tile)
                self.drawn_tile = None
            self.turn = seat
        elif name == "ActionChiPengGang":
            self.melds[seat].append(deepcopy(data))
            tiles, froms = data.get("tiles", []), data.get("froms", [])
            if len(tiles) != len(froms):
                self.invalidate("Meld tile origins are missing")
            else:
                self._mark_called_discard(seat, tiles, froms)
                if seat == self.seat:
                    self.drawn_tile = None
                    for tile, origin in zip(tiles, froms):
                        if origin == seat:
                            self._remove(tile)
            self.turn = seat
        elif name == "ActionBaBei":
            self.norths[seat] += 1
            if seat == self.seat:
                self._remove("4z")
                self.drawn_tile = None
        elif name == "ActionAnGangAddGang":
            self._kan(seat, data)
            if seat == self.seat:
                self.drawn_tile = None
            self.turn = seat
        elif name in ("ActionHule", "ActionNoTile", "ActionLiuJu"):
            if name == "ActionHule":
                self.round["liqibang"] = 0
            if self.status != "incomplete":
                self.status = "round_ended"
            self.operations = None
        elif name != "ActionNewRound":
            self.invalidate(f"Unsupported action: {name}")
        return True

    def validate(self):
        if self.seat is not None and not 0 <= self.seat < self.player_count:
            self.invalidate("Own seat is outside the player count")
        valid = {str(number) + suit for suit in "mps" for number in range(1, 10)}
        valid |= {"0" + suit for suit in "mps"}
        valid |= {str(number) + "z" for number in range(1, 8)}
        tiles = list(self.hand) + list(self.doras)
        tiles.extend(item["tile"] for river in self.discards for item in river)
        tiles.extend(tile for melds in self.melds for meld in melds for tile in meld.get("tiles", []))
        if any(tile not in valid for tile in tiles):
            self.invalidate("Visible state contains an invalid tile")
            return
        counts, _ = self.visible_tiles()
        if any(count > 4 for count in counts.values()):
            self.invalidate("Visible tile count exceeds four copies")

    def visible_tiles(self):
        counts = Counter(self._tile_kind(tile) for tile in self.hand)
        complete = self.status in ("tracking", "round_ended", "match_ended")
        for river in self.discards:
            for discard in river:
                if discard.get("called") is None:
                    complete = False
                elif not discard["called"]:
                    counts[self._tile_kind(discard["tile"])] += 1
        for melds in self.melds:
            for meld in melds:
                counts.update(self._tile_kind(tile) for tile in meld.get("tiles", []))
        counts["4z"] += sum(self.norths)
        counts.update(self._tile_kind(tile) for tile in self.doras)
        # Snapshot rivers do not identify called tiles reliably. Counts then
        # represent only a lower bound and are explicitly not complete.
        return dict(sorted((tile, count) for tile, count in counts.items() if count)), complete

    def snapshot(self):
        visible, complete = self.visible_tiles()
        return deepcopy({"visible_tile_counts": visible, "visibility_complete": complete, "player_count": self.player_count, "status": self.status, "issues": self.issues, "seat": self.seat,
                         "step": self.last_step, "round": self.round, "hand": self.hand, "opening_hand": self.opening_hand, "scoring_context": self.scoring_context.snapshot(), "win_source": self.win_source,
                         "discards": self.discards, "melds": self.melds, "norths": self.norths,
                         "scores": self.scores, "doras": self.doras,
                         "left_tile_count": self.left_tile_count, "turn": self.turn,
                         "operations": self.operations, "player_metadata": self.player_metadata,
                         "riichi": self.riichi, "drawn_tile": self.drawn_tile, "furiten": self.furiten})
