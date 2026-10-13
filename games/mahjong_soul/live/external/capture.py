"""Append-only capture writer, independent of mitmproxy for offline tests."""

import base64
import json
import ipaddress
import re
import logging
from pathlib import Path

from games.mahjong_soul.live.external.liqi import decode_envelope
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.reader import GameReader


class CaptureWriter:
    def __init__(self, path, schema=None, seat=None, action_encoding="xor"):
        self.path = Path(path)
        self.schema = schema
        self.seat = seat
        self.action_encoding = action_encoding
        self.reader = GameReader(schema, seat, action_encoding) if schema is not None else None
        self.connections = self.reader.connections if self.reader else {}

    def close_connection(self, connection):
        if self.reader:
            self.reader.close_connection(connection)

    def record(self, *, connection, host, content, from_client, timestamp, is_text=False):
        record = {
            "format_version": 1,
            "connection": connection,
            "host": host,
            "timestamp": timestamp,
            "direction": "client" if from_client else "server",
            "size": len(content),
            "is_text": is_text,
            "raw_base64": base64.b64encode(content).decode("ascii"),
        }
        try:
            if self.schema is None:
                if is_text:
                    raise ValueError("Text WebSocket message")
                record["liqi"] = decode_envelope(content)
            else:
                record.update(self.reader.read(connection, content, from_client, is_text))
        except (ValueError, UnicodeError) as error:
            record["decode_error"] = str(error)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record


class MahjongSoulCapture:
    def __init__(self):
        self.writer = None

    def load(self, loader):
        loader.add_option("mahjong_capture_output", str,
                          "logs/mahjong_soul/capture.jsonl", "Capture output path")
        loader.add_option("mahjong_capture_hosts", str,
                          "mahjongsoul.com,maj-soul.com,majsoul.com,yo-star.com",
                          "Comma-separated allowed host suffixes")
        loader.add_option("mahjong_capture_schema", str, "", "Path to client liqi.json")
        loader.add_option("mahjong_capture_seat", int, -1, "Own absolute seat, 0-3; -1 unknown")
        loader.add_option("mahjong_action_encoding", str, "xor", "Live action encoding: xor or plain")

    def configure(self, updated):
        from mitmproxy import ctx

        if self.writer is None or any(name in updated for name in (
                "mahjong_capture_output", "mahjong_capture_schema", "mahjong_capture_seat",
                "mahjong_action_encoding")):
            schema = LiqiSchema.load(ctx.options.mahjong_capture_schema) if ctx.options.mahjong_capture_schema else None
            seat = ctx.options.mahjong_capture_seat
            if seat not in (-1, 0, 1, 2, 3):
                raise ValueError("Own seat must be -1 or 0-3")
            self.writer = CaptureWriter(ctx.options.mahjong_capture_output, schema,
                                        None if seat == -1 else seat, ctx.options.mahjong_action_encoding)

    def websocket_end(self, flow):
        if self.writer is not None:
            self.writer.close_connection(flow.id)

    def websocket_message(self, flow):
        from mitmproxy import ctx

        host = flow.request.host.lower().rstrip(".")
        allowed = [item.strip().lower().rstrip(".")
                   for item in ctx.options.mahjong_capture_hosts.split(",") if item.strip()]
        allowed_host = any(host == suffix or host.endswith("." + suffix) for suffix in allowed)
        process_scoped = any(re.fullmatch(r"local:[A-Za-z0-9_.-]+", mode)
                             for mode in getattr(ctx.options, "mode", []))
        if not allowed_host and process_scoped:
            try:
                ipaddress.ip_address(host.strip("[]"))
                allowed_host = True
            except ValueError:
                pass
        if not allowed_host:
            return
        message = flow.websocket.messages[-1]
        try:
            writer = self.writer or CaptureWriter(ctx.options.mahjong_capture_output)
            record = writer.record(
                connection=flow.id, host=host, content=message.content,
                from_client=message.from_client, timestamp=message.timestamp,
                is_text=message.is_text)
        except OSError as error:
            logging.error("Mahjong capture write failed: %s", error)
            return
        decoded = record.get("liqi", {})
        logging.info("Mahjong %s %s %s (%s bytes)", record["direction"],
                     decoded.get("method", "undecoded"), decoded.get("action", ""),
                     record["size"])


addons = [MahjongSoulCapture()]
