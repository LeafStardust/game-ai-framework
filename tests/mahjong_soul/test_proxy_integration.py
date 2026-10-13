"""Exercise the real capture addon through a loopback WebSocket proxy."""

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import pytest

from tests.mahjong_soul.test_decoder_state import action, blob, wrapper


def read_exact(stream, count):
    output = b""
    while len(output) < count:
        chunk = stream.recv(count - len(output))
        if not chunk:
            raise AssertionError("Socket closed before expected data")
        output += chunk
    return output


def read_headers(stream):
    output = b""
    while not output.endswith(b"\r\n\r\n"):
        output += read_exact(stream, 1)
        if len(output) > 16384:
            raise AssertionError("Oversized handshake")
    return output


def read_frame(stream):
    first, second = read_exact(stream, 2)
    assert first == 0x82
    size = second & 127
    if size == 126:
        size = int.from_bytes(read_exact(stream, 2), "big")
    assert size < 65536
    mask = read_exact(stream, 4) if second & 128 else None
    payload = read_exact(stream, size)
    return bytes(value ^ mask[index % 4] for index, value in enumerate(payload)) if mask else payload


def frame(payload, masked=False):
    mask = b"abcd"
    size = len(payload)
    header = bytes([0x82, (128 if masked else 0) | (size if size < 126 else 126)])
    if size >= 126:
        header += size.to_bytes(2, "big")
    if masked:
        return header + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    return header + payload


@pytest.mark.skipif(importlib.util.find_spec("mitmproxy") is None, reason="Optional capture dependencies not installed")
def test_real_proxy_forwards_and_records_game_events(tmp_path):
    root = Path(__file__).resolve().parents[2]
    capture = tmp_path / "capture.jsonl"
    initial = wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))
    request = wrapper(2, ".lq.FastTest.checkNetworkDelay", b"", request_id=17)
    response = wrapper(3, "", b"", request_id=17)
    received = []
    failures = []
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.settimeout(15)
    server_port = server.getsockname()[1]
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        proxy_port = port_probe.getsockname()[1]

    def serve():
        try:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(10)
                headers = read_headers(connection).decode()
                key = next(line.split(":", 1)[1].strip() for line in headers.split("\r\n") if line.lower().startswith("sec-websocket-key:"))
                accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
                connection.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + accept + "\r\n\r\n").encode())
                connection.sendall(frame(initial))
                received.append(read_frame(connection))
                connection.sendall(frame(response))
                # Keep the upgraded connection alive until the client closes it.
                connection.recv(1024)
        except BaseException as error:
            failures.append(error)
        finally:
            server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    command = [sys.executable, "-m", "games.mahjong_soul.live", "--port", str(proxy_port),
               "--schema", str(root / "liqi-reference.json"), "--hosts", "127.0.0.1",
               "--seat", "0", "--output", str(capture), "--confdir", str(tmp_path / "proxy-config")]
    with (tmp_path / "proxy.log").open("w") as log:
        process = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while True:
                assert process.poll() is None, (tmp_path / "proxy.log").read_text()
                try:
                    client = socket.create_connection(("127.0.0.1", proxy_port), timeout=1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise AssertionError("Proxy did not start")
                    time.sleep(0.1)
            with client:
                client.settimeout(10)
                handshake = (f"GET http://127.0.0.1:{server_port}/game HTTP/1.1\r\nHost: 127.0.0.1:{server_port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n")
                client.sendall(handshake.encode())
                assert b"101" in read_headers(client)
                assert read_frame(client) == initial
                client.sendall(frame(request, masked=True))
                assert read_frame(client) == response
            thread.join(timeout=5)
            assert not thread.is_alive()
            assert not failures
            assert received == [request]
            rows = [json.loads(line) for line in capture.read_text().splitlines()]
            assert len(rows) == 3
            assert [row["direction"] for row in rows] == ["server", "client", "server"]
            assert rows[0]["liqi"]["events"][0]["name"] == "ActionNewRound"
            assert rows[0]["state"]["hand"] == ["1m"]
            assert rows[-1]["liqi"]["method"] == ".lq.FastTest.checkNetworkDelay"
            assert rows[-1]["state"]["status"] == "tracking"
            assert all("decode_error" not in row for row in rows)
        finally:
            if os.name == "nt" and process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10)
            elif process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            server.close()
