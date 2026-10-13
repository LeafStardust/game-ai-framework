"""Connection-scoped request correlation and live/restore action decoding."""

import base64

from games.mahjong_soul.live.external.liqi import decode_envelope


def action_bytes(data):
    """Undo the position-dependent XOR used in live ActionPrototype data."""
    keys = (132, 94, 78, 66, 57, 162, 31, 96, 28)
    base = len(data) ^ 23
    return bytes(byte ^ ((base + index * 5 + keys[index % 9]) & 255)
                 for index, byte in enumerate(data))


class LiqiDecoder:
    def __init__(self, schema, action_encoding="xor"):
        if action_encoding not in ("xor", "plain"):
            raise ValueError("Action encoding must be xor or plain")
        self.schema = schema
        self.action_encoding = action_encoding
        self.pending = {}
        self.account_id = None

    def decode(self, content, from_client):
        envelope = decode_envelope(content)
        method = envelope["method"]
        request_id = envelope["request_id"]
        kind = envelope["kind"]
        payload = base64.b64decode(envelope["payload_base64"])
        if kind == "request":
            route = self.schema.methods.get(method)
            if route is None:
                raise ValueError(f"Unknown RPC: {method}")
            message_type, response_type = route
            # Response travels in the opposite direction, keyed independently.
            self.pending[(not from_client, request_id)] = (method, response_type)
        elif kind == "response":
            route = self.pending.pop((from_client, request_id), None)
            if route is None:
                raise ValueError(f"Unmatched response: {request_id}")
            method, message_type = route
        else:
            message_type = method.lstrip(".")
        data = self.schema.decode(message_type, payload)
        if method == ".lq.FastTest.authGame":
            if kind == "request" and from_client:
                self.account_id = data.get("account_id")
            elif kind == "response" and not from_client and self.account_id:
                seats = data.get("seat_list", [])
                if self.account_id in seats:
                    envelope["own_seat"] = seats.index(self.account_id)
        envelope["method"] = method
        envelope["data"] = data
        events = []
        if method == ".lq.ActionPrototype":
            events.append(self._action(data, live=True))
        restore = data.get("game_restore")
        if isinstance(restore, dict):
            for action in restore.get("actions", []):
                events.append(self._action(action, live=False))
            envelope["restore_has_snapshot"] = bool(restore.get("snapshot"))
            if "snapshot" in restore:
                envelope["restore_snapshot"] = restore["snapshot"]
        envelope["events"] = events
        return envelope

    def _action(self, action, live):
        name = action["name"].split(".")[-1]
        encoded = base64.b64decode(action.get("data", ""), validate=True)
        if live and self.action_encoding == "xor":
            encoded = action_bytes(encoded)
        return {"name": name, "step": action.get("step", 0),
                "source": "live" if live else "restore",
                "data": self.schema.decode(f"lq.{name}", encoded)}
