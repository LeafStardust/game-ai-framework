"""Append-only capture writer, independent of mitmproxy for offline tests."""

import base64
import json
import logging
from pathlib import Path

from games.mahjong_soul.live.external.liqi import decode_envelope


class CaptureWriter:
    def __init__(self, path):
        self.path = Path(path)

    def record(self, *, connection, host, content, from_client, timestamp, is_text=False):
        record = {
            "format_version": 1,
            "connection": connection,
            "host": host,
            "timestamp": timestamp,
            "direction": "client" if from_client else "server",
            "size": len(content),
            "raw_base64": base64.b64encode(content).decode("ascii"),
        }
        try:
            if is_text:
                raise ValueError("Text WebSocket message")
            record["liqi"] = decode_envelope(content)
        except (ValueError, UnicodeError) as error:
            record["decode_error"] = str(error)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record


class MahjongSoulCapture:
    def load(self, loader):
        loader.add_option("mahjong_capture_output", str,
                          "logs/mahjong_soul/capture.jsonl", "Capture output path")
        loader.add_option("mahjong_capture_hosts", str,
                          "mahjongsoul.com,maj-soul.com,majsoul.com,yo-star.com",
                          "Comma-separated allowed host suffixes")

    def websocket_message(self, flow):
        from mitmproxy import ctx

        host = flow.request.host.lower().rstrip(".")
        allowed = [item.strip().lower().rstrip(".")
                   for item in ctx.options.mahjong_capture_hosts.split(",") if item.strip()]
        if not any(host == suffix or host.endswith("." + suffix) for suffix in allowed):
            return
        message = flow.websocket.messages[-1]
        try:
            record = CaptureWriter(ctx.options.mahjong_capture_output).record(
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
