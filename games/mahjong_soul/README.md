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

From the Mahjong Soul worktree root, using Python 3.12 or newer:

```powershell
.\MahjongSoulSetup.bat
.\MahjongSoulCapture.bat --check
```

Setup creates a worktree-local `.venv` and installs only the capture dependencies
there. It does not alter Balatro's Python environment. The capture launcher uses
the committed `liqi-reference.json` by default; its current Steam compatibility
still needs live verification. Override it with `--schema path/to/liqi.json` or
use `--raw-only` for envelope-only recording.

To capture a specific Steam game process directly on Windows:

```powershell
.\MahjongSoulCapture.bat --process Jantama_MahjongSoul.exe
```

Use the actual executable name shown in Task Manager, or its numeric PID. Only
one explicit target is accepted; wildcard, exclusion and comma-separated target
specifications are rejected. Numeric-IP WebSocket destinations are accepted in
this explicitly process-scoped mode; regular mode retains hostname filtering. This uses mitmproxy local capture mode, avoiding an
external process redirector. It may require Windows elevation. See
https://docs.mitmproxy.org/stable/concepts/modes/#local-capture.

Alternatively, start a regular HTTP proxy for an externally routed game client:

```powershell
.\MahjongSoulCapture.bat
```

Regular proxy address: `127.0.0.1:8080`. Each run creates a new timestamped JSONL
under `logs/mahjong_soul/`; `--output` and `--port` override these defaults.
Proxy configuration and certificates stay in `logs/mahjong_soul/proxy/`, rather
than the global mitmproxy configuration folder. Override with `--confdir` if
needed. On first actual startup, mitmproxy generates `mitmproxy-ca-cert.cer` there;
certificate trust for the Steam client's TLS must be configured separately.
Neither setup nor the launcher automatically installs a root certificate.
`--check` validates dependencies/schema without starting traffic interception.

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

In regular proxy mode, Steam traffic must be routed explicitly through the proxy
using an application redirector such as Proxifier. Target the actual Mahjong Soul executable, not Steam
as a whole, and exclude localhost/loopback destinations. A system proxy setting
alone may not route the Steam game. Trust the proxy certificate in the certificate
store used by the client; use this worktree's generated certificate. The launcher does not change system routing or certificate trust.
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

## Live state reader

In a second terminal in this worktree:

```powershell
.\MahjongSoulReader.bat
```

The viewer follows the newest timestamped capture, re-decodes it through the same
`GameReader` used by the capture addon, and refreshes your hand, last drawn tile,
furiten, rivers, melds, dora indicators, scores, norths, riichi status, and available
operations. Called river tiles are marked `*` so consumers can avoid counting them
again in melds. Known operation types have readable labels; unknown types retain
their numeric codes. Diagnostics remain visible, and unrelated lobby errors do
not invalidate a healthy game connection.

Use `--file path/to/capture.jsonl` to inspect a saved capture, `--once` for one
summary, or `--once --json` for a structured state/diagnostic report. The follower
waits for complete JSONL rows, reports malformed rows, resets after truncation,
and switches to newly created live captures. It does not send game actions.

The reusable Python interface is `GameReader(schema, seat=None)`, then
`consume(capture_row)` or `read(connection, content, from_client)`, and `snapshot()`.
The state also includes normalized `visible_tile_counts` (red fives counted as
fives) and `visibility_complete`. Opponent concealed hands are never counted.
Called discards are counted in their meld only; north extractions and dora
indicators are counted as visible tiles. Snapshot rivers with unknown called
flags produce a lower bound with `visibility_complete=false`. Invalid tiles and
more than four visible copies mark state incomplete. Opponent concealed kan
retains its tile kind while explicitly leaving red-five composition unknown.

It maintains per-connection decoders and separates lobby diagnostics from the
latest game state. `NotifyGameEndResult` transitions the state to `match_ended`.
Ordinary exhaustive draws restore scores using old-score/delta vectors; ambiguous
multiple nagashi settlements are flagged incomplete until live-verified.

## Validation status

Offline tests cover kan/red-five handling, snapshot restoration, framing, malformed fields, packed/signed values, live versus
reconnect encoding, connection/direction-scoped correlation, seat inference,
hand updates, hidden draws, duplicate steps, gaps, and host filtering. A real
loopback WebSocket integration test verifies addon loading, unchanged bidirectional
forwarding, schema decoding, state recording, and test-process cleanup. The public
reference schema has also been loaded and smoke-tested. Live Steam capture has
been verified on one Steam three-player AI match: all 77 game actions decoded
and replayed without gaps, with correct final scores and three-seat north counts.
See [live validation](LIVE_VALIDATION.md). Four-player matches, kans, and reconnects
still require live verification. One unrelated lobby activity reply did not match
the reference schema; its raw frame and decoding error were retained.

Protocol references:
- https://github.com/MahjongRepository/mahjong_soul_api
- https://github.com/747929791/majsoul_wrapper
- https://docs.mitmproxy.org/stable/api/mitmproxy/websocket.html
- https://github.com/shinkuan/Akagi/blob/v3/src/bridge/majsoul/parser.rs (wire-format reference)
