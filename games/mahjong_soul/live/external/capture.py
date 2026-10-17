"""Append-only capture writer, independent of mitmproxy for offline tests."""

import asyncio
import base64
import json
import ipaddress
import re
import logging
import time
from pathlib import Path

from games.mahjong_soul.live.external.liqi import decode_envelope
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.reader import GameReader
from games.mahjong_soul.live.runtime.input import board_token


class CaptureWriter:
    def __init__(self, path, schema=None, seat=None, action_encoding="xor"):
        self.path = Path(path)
        self.schema = schema
        self.seat = seat
        self.action_encoding = action_encoding
        self.reader = GameReader(schema, seat, action_encoding) if schema is not None else None
        self.connections = self.reader.connections if self.reader else {}
        self.captured_connections = set()

    def close_connection(self, connection, timestamp=None):
        if connection not in self.captured_connections:
            return
        self.captured_connections.remove(connection)
        state = self.reader.close_connection(connection) if self.reader else None
        record = {"format_version": 2, "event": "connection_closed", "connection": connection,
                  "timestamp": time.time() if timestamp is None else timestamp}
        if state is not None:
            record["state"] = state
        self._append(record)
        return record

    def health(self, timestamp=None):
        if not self.path.exists():return
        info=self.path.stat()
        value={"version":1,"timestamp":time.time() if timestamp is None else timestamp,
               "capture":str(self.path.resolve()),"size":info.st_size,"identity":[info.st_dev,info.st_ino],
               "connections":sorted(self.captured_connections),
               "board_token":board_token(self.reader.snapshot()) if self.reader else None}
        target=self.path.with_suffix(self.path.suffix+".health.json")
        temporary=target.with_suffix(".tmp")
        temporary.write_text(json.dumps(value),encoding="utf-8");temporary.replace(target)

    def _append(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.health()

    def record(self, *, connection, host, content, from_client, timestamp, is_text=False):
        record = {
            "format_version": 2,
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
        self.captured_connections.add(connection)
        self._append(record)
        return record


class MahjongSoulCapture:
    def __init__(self):
        self.writer = None
        self.health_task = None

    async def running(self):
        async def heartbeat():
            while True:
                try:
                    if self.writer is not None:self.writer.health()
                except OSError as error:logging.error("Capture health write failed: %s",error)
                await asyncio.sleep(.5)
        self.health_task=asyncio.create_task(heartbeat())

    def done(self):
        if self.health_task is not None:self.health_task.cancel()

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
