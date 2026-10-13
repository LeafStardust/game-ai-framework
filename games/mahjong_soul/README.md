# Mahjong Soul Steam capture

## First milestone

Capture-only local proxy. Writes append-only JSONL with timestamps, connection IDs,
direction, original frame bytes (base64), and decoded Liqi envelope metadata.
ActionPrototype notifications expose action names and step numbers. Inner action
payloads remain opaque: tile/state decoding and request-response correlation are
not implemented yet. Unknown or malformed frames are retained for diagnosis.

## Run

From the repository root, using Python 3.12 or newer:

```powershell
py -m pip install -r games/mahjong_soul/setup/requirements.txt
py -m games.mahjong_soul.live
```

Proxy address: `127.0.0.1:8080`. Output: `logs/mahjong_soul/capture.jsonl`.
Use `--port` and `--output` to override these defaults.

Steam traffic must be routed explicitly through the proxy using an application
redirector such as Proxifier. Target the actual Mahjong Soul executable, not Steam
as a whole, and exclude localhost/loopback destinations. A system proxy setting
alone may not route the Steam game. Trust the proxy certificate in the certificate
store used by the client; mitmproxy generates it under its user configuration
directory. The launcher does not change system routing or certificate trust.
If the client refuses the certificate, stop and diagnose rather than disable TLS
verification. See https://docs.mitmproxy.org/stable/concepts/certificates/.

Start capture before launching the game and enter an AI match. The terminal should
show `.lq.ActionPrototype` and action names; JSONL should grow as players act.
If the file stays empty, check routing, certificate trust, and actual destination
hosts. Host suffix filtering is configured by the mitmproxy option
`mahjong_capture_hosts`; URLs, headers, and cookies are not recorded. Raw frames
can still contain credentials and account information, so keep captures local.

Stop with Ctrl+C, remove the game routing rule, and remove certificate trust when
no longer needed. Captures are under the repository's ignored `logs/` directory.

## Validation status

Synthetic framing and capture tests cover malformed frames, append-only recording,
host filtering, and unchanged forwarded content. Live Steam capture has not yet
been verified. Full state decoding requires confirming the current client schema
and action encoding from a real capture.

Protocol references:
- https://github.com/MahjongRepository/mahjong_soul_api
- https://github.com/747929791/majsoul_wrapper
- https://docs.mitmproxy.org/stable/api/mitmproxy/websocket.html
