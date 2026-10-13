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
        self.actions = Counter()
        self.last_event = None

    def close_connection(self, connection):
        # Keep the last visible snapshot for display after the socket closes.
        entry = self.connections.pop(connection, None)
        if entry and connection == self.latest_game_connection:
            self.closed_state = entry[1].snapshot()

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
            if "own_seat" in decoded and self.seat is None:
                state.seat = decoded["own_seat"]
            if "restore_snapshot" in decoded:
                next_step = decoded["events"][0]["step"] if decoded["events"] else None
                state.restore(decoded["restore_snapshot"], next_step)
            for event in decoded["events"]:
                self.actions[event["name"]] += 1
                state.apply(event)
                self.last_event = {"name": event["name"], "step": event["step"]}
            state.validate()
            if method == ".lq.NotifyGameEndResult":
                state.operations = None
                if state.status != "incomplete":
                    state.status = "match_ended"
            if decoded["events"] or "restore_snapshot" in decoded or method.startswith(".lq.FastTest.") or method == ".lq.NotifyGameEndResult":
                self.latest_game_connection = connection
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
        if row["direction"] not in ("client", "server"):
            raise ValueError("Invalid capture direction")
        if not isinstance(row["connection"], str) or not row["connection"]:
            raise ValueError("Invalid capture connection")
        return self.read(row["connection"], base64.b64decode(row["raw_base64"], validate=True),
                         row["direction"] == "client", row.get("is_text", False))

    def snapshot(self):
        entry = self.connections.get(self.latest_game_connection)
        state = entry[1].snapshot() if entry else deepcopy(getattr(self, "closed_state", None))
        return {"frames": self.frames, "actions": dict(self.actions), "last_event": deepcopy(self.last_event), "game_connection": self.latest_game_connection,
                "decode_errors": [{"method": method, "error": error, "count": count}
                                  for (method, error), count in self.errors.items()], "state": state}
