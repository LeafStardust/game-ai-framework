"""Shared read-only game reader used by live capture and saved-capture monitoring."""

import base64
from collections import Counter
from copy import deepcopy

from games.mahjong_soul.live.external.decoder import LiqiDecoder
from games.mahjong_soul.live.external.liqi import decode_envelope
from games.mahjong_soul.live.runtime.state import GameState


class GameReader:
    def __init__(self, schema, seat=None, action_encoding="xor"):
        self.schema = schema
        self.seat = seat
        self.action_encoding = action_encoding
        self.connections = {}
        self.latest_game_connection = None
        self.frames = 0
        self.errors = Counter()
        self.warnings = Counter()
        self.actions = Counter()
        self.last_event = None
        self.connection_events = {}
        self.closed_connections = 0
        self.game_generations = Counter()
        self.cancel_requests = {}
        self.game_rules = {}

    def close_connection(self, connection):
        # Keep the last visible snapshot for display after the socket closes.
        entry = self.connections.pop(connection, None)
        self.cancel_requests.pop(connection, None)
        if entry:
            self.closed_connections += 1
            if connection == self.latest_game_connection:
                if entry[1].status not in ("match_ended", "round_ended"):
                    entry[1].invalidate("Game connection closed; awaiting restoration")
                entry[1].operations = None
                self.closed_state = entry[1].snapshot()
            return entry[1].snapshot()
        return None

    def read(self, connection, content, from_client, is_text=False):
        self.frames += 1
        if connection not in self.connections:
            self.connections[connection] = (LiqiDecoder(self.schema, self.action_encoding), GameState(self.seat))
        decoder, state = self.connections[connection]
        result = {}
        method = ""
        try:
            if is_text:
                raise ValueError("Text WebSocket message")
            envelope = decode_envelope(content)
            method = envelope["method"]
            if envelope["kind"] == "response":
                pending = decoder.pending.get((from_client, envelope["request_id"]))
                if pending:
                    method = pending[0]
            decoded = decoder.decode(content, from_client)
            result["liqi"] = decoded
            cancellations = self.cancel_requests.setdefault(connection, {})
            request_id = decoded.get("request_id")
            if decoded["kind"] == "request" and from_client:
                cancellations.pop(request_id, None)
                if method == ".lq.FastTest.inputChiPengGang" and decoded.get("data", {}).get("cancel_operation") is True:
                    cancellations[request_id] = state.last_step
            elif decoded["kind"] == "response" and not from_client and method == ".lq.FastTest.inputChiPengGang":
                request_step = cancellations.pop(request_id, None)
                if request_step is not None and request_step == state.last_step and not decoded.get("data", {}).get("error", {}).get("code", 0):
                    state.operations = None
            if decoded.get("schema_warning"):
                self.warnings[(decoded["method"], decoded["schema_warning"])] += 1
            if decoded["method"] == ".lq.FastTest.authGame" and decoded["kind"] == "response":
                self.game_generations[connection] += 1
                detail=decoded.get("data",{}).get("game_config",{}).get("mode",{}).get("detail_rule",{})
                kuitan=detail.get("shiduan")
                self.game_rules[connection]={"open_tanyao":bool(kuitan) if type(kuitan) in (bool,int) and kuitan in (0,1) else None}
                cancellations.clear()
                inferred_seat = self.seat if self.seat is not None else decoded.get("own_seat")
                seats = decoded.get("data", {}).get("seat_list", [])
                player_count = len(seats) if len(seats) in (3, 4) else state.player_count
                state.__init__(inferred_seat, player_count)
                self.connection_events.pop(connection, None)
                if decoded.get("data", {}).get("error", {}).get("code", 0):
                    state.invalidate("Game authentication failed")
            if "restore_snapshot" in decoded:
                next_step = decoded["events"][0]["step"] if decoded["events"] else None
                state.restore(decoded["restore_snapshot"], next_step)
            for event in decoded["events"]:
                self.actions[event["name"]] += 1
                state.apply(event)
                self.connection_events[connection] = {"name": event["name"], "step": event["step"]}
            state.validate()
            if method == ".lq.NotifyGameEndResult":
                state.operations = None
                if state.status != "incomplete":
                    state.status = "match_ended"
            strong_update = decoded["events"] or "restore_snapshot" in decoded or (method == ".lq.FastTest.authGame" and decoded["kind"] == "response")
            end_update = method == ".lq.NotifyGameEndResult" and self.latest_game_connection in (None, connection)
            if strong_update or end_update:
                self.latest_game_connection = connection
            self.last_event = deepcopy(self.connection_events.get(self.latest_game_connection))
        except (ValueError, UnicodeError) as error:
            result["decode_error"] = str(error)
            result["decode_method"] = method or None
            self.errors[(method or "unknown", str(error))] += 1
            game_related = method.startswith(".lq.FastTest.") or method.startswith(".lq.Action") or method.startswith(".lq.NotifyGame")
            if game_related or (not method and state.last_step is not None):
                state.invalidate("An undecoded game frame was encountered")
        result["state"] = state.snapshot()
        return result

    def consume(self, row):
        if row.get("event") == "connection_closed":
            if not isinstance(row.get("connection"), str) or not row["connection"]:
                raise ValueError("Invalid capture connection")
            state = self.close_connection(row["connection"])
            return {"event": "connection_closed", "state": state}
        if row.get("event"):
            raise ValueError("Unknown capture control event")
        if row["direction"] not in ("client", "server"):
            raise ValueError("Invalid capture direction")
        if not isinstance(row["connection"], str) or not row["connection"]:
            raise ValueError("Invalid capture connection")
        return self.read(row["connection"], base64.b64decode(row["raw_base64"], validate=True),
                         row["direction"] == "client", row.get("is_text", False))

    def snapshot(self):
        entry = self.connections.get(self.latest_game_connection)
        state = entry[1].snapshot() if entry else deepcopy(getattr(self, "closed_state", None))
        if state is not None:state["rules"]=deepcopy(self.game_rules.get(self.latest_game_connection,{"open_tanyao":None}))
        ready = bool(entry and state and state["status"] == "tracking" and state["seat"] is not None
                     and not state["issues"] and state["visibility_complete"])
        return {"game_generation": self.game_generations[self.latest_game_connection], "state_ready": ready, "frames": self.frames, "actions": dict(self.actions), "last_event": deepcopy(self.last_event), "game_connection": self.latest_game_connection,
                "connection_open": bool(entry), "closed_connections": self.closed_connections,
                "schema_warnings": [{"method": method, "warning": warning, "count": count} for (method, warning), count in self.warnings.items()],
                "decode_errors": [{"method": method, "error": error, "count": count}
                                  for (method, error), count in self.errors.items()], "state": state}
