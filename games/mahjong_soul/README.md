# Mahjong Soul Steam capture

## Capture and decoding

Capture-only local proxy. Writes append-only JSONL with timestamps, connection IDs,
direction, original frame bytes (base64), and decoded Liqi envelope metadata.
Without a schema, ActionPrototype notifications expose action names and step
numbers only. With the client's protobufjs `liqi.json`, the decoder also handles
typed payloads, packed numeric fields, per-connection request/response matching,
live action XOR encoding, and unencoded reconnect actions. Unknown or malformed
frames are retained for diagnosis and mark state incomplete.

## Run

From the repository root, using Python 3.12 or newer:

```powershell
py -m pip install -r games/mahjong_soul/setup/requirements.txt
py -m games.mahjong_soul.live
```

Proxy address: `127.0.0.1:8080`. Output: `logs/mahjong_soul/capture.jsonl`.
Use `--port` and `--output` to override these defaults.

For typed events and state snapshots, obtain the `liqi.json` schema matching your
client and save it locally. A public reference schema is available at
https://github.com/MahjongRepository/mahjong_soul_api/blob/master/ms/liqi.json;
its compatibility with the current Steam build must still be verified. Then run:

```powershell
py -m games.mahjong_soul.live --schema path/to/liqi.json
```

Own absolute seat is inferred from captured `FastTest.authGame` traffic. Start
capture before login/game entry so that request and response are both observed.
If that exchange was missed, specify `--seat 0` (or 1, 2, 3) using the actual
absolute seat. This is not simply the screen position of the player's hand.
Use `--action-encoding plain` only for builds confirmed to send unencoded live
actions; the default is `xor`. Reconnect actions always decode without XOR.

Each decoded row includes its events and a visible-state snapshot: own hand,
discard rivers, meld events, north extractions, scores, dora, wall count, and
available operations. Unknown opponent draws remain unknown. The tracker handles
new round, draw, discard, chi/pon/open-kan, north extraction, and round-end events.
Concealed kan removes four matching own tiles while retaining red fives; added
kan upgrades a matching pon and removes only the added own tile. Invalid kan
events mark state incomplete without guessing which tiles to remove.

Reconnect snapshots replace the tracked hand, scores, rivers, melds, round, and
dora before following restore actions are applied. When no following action is
provided, the next live action establishes the step baseline. Historical discard
riichi/tsumogiri flags are left unknown when the snapshot does not supply them;
snapshot player riichi positions are retained separately as metadata. Annotated
snapshot discards and unsupported meld types (including special-mode or north
extraction representations not yet verified) mark state incomplete. Step gaps
and missing own tiles also mark state incomplete. A new round resets that status.
Do not use incomplete state for agent decisions.

Replay a raw capture offline into a **new** output file:

```powershell
py -m games.mahjong_soul.live.runtime.replay logs/mahjong_soul/capture.jsonl --schema path/to/liqi.json --output logs/mahjong_soul/decoded.jsonl
```

Replay accepts the same `--seat` and `--action-encoding` options. It never modifies
the source capture and refuses an existing output path.

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

Offline tests cover kan/red-five handling, snapshot restoration, framing, malformed fields, packed/signed values, live versus
reconnect encoding, connection/direction-scoped correlation, seat inference,
hand updates, hidden draws, duplicate steps, gaps, and host filtering. The public
reference schema has also been loaded and smoke-tested. Live Steam capture has
not yet been verified; current client schema/encoding and observed state must be
checked against an AI match before connecting decision logic.

Protocol references:
- https://github.com/MahjongRepository/mahjong_soul_api
- https://github.com/747929791/majsoul_wrapper
- https://docs.mitmproxy.org/stable/api/mitmproxy/websocket.html
- https://github.com/shinkuan/Akagi/blob/v3/src/bridge/majsoul/parser.rs (wire-format reference)
