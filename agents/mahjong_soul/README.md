# Mahjong Soul policy integration

`policy.Policy` defines `choose(request) -> action`. `proposal_from_policy` gives the policy an independent request copy and wraps its chosen action in the original request/board identity. `evaluate.decide` then re-reads a caller-provided current snapshot and validates the response, including elapsed policy time. This path returns a nonexecutable intent and has no input backend. A future live caller must establish capture freshness separately.

`BaselinePolicy` is an integration fixture: take offered Tsumo/Ron, otherwise discard the exact drawn tile if allowed, otherwise choose a deterministic permitted discard, or Skip an opponent call. It preserves a red five over an ordinary tile when making its deterministic fallback selection. It never selects Chi/Pon/kan/Riichi, computes no shanten and makes no defensive assessment. It is not a trained or strength-tested player.

Run aggregate offline contract evaluation from the Mahjong worktree:

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.evaluate logs/mahjong_soul/capture-20261017-161959-450139.jsonl
```

Use `--schema <path>` to select another schema or `--output <new-path>` to write a new aggregate JSON report. Existing reports are refused. Output contains counts, not hand histories or authentication payloads. Evaluation decodes rows through GameReader, deduplicates identical board tokens, creates requests only for ready own offers, invokes the policy and validates every response. Unsupported offers, malformed rows, unfinished capture rows, game decoding errors, policy failures or zero validated proposals cause a nonzero CLI exit. A closed final connection is reported but does not invalidate earlier offline decisions.

The 2026-10-17 local capture produced 131 requests and 131 validated proposals: 106 discards, 20 skips and 5 Ron choices; no unsupported requests, malformed rows, game decoding errors or policy failures. Captured actions are not changed by proposed decisions, so later recorded states are still the human player's trajectory. These totals measure interface coverage only, not simulated outcomes, agreement, rewards, win rate or policy quality.

Next is a continuously running read-only shadow consumer that retains the policy and follows new reader state. Actual execution still needs verified visual tile/action binding and one persistent guarded input controller.


## Read-only shadow runner

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.shadow --duration 3600
```

Start the process-scoped Steam capture first. The shadow runner follows the newest `capture-*.jsonl` in this worktree, or `--file <path>` pins one capture. `--once` performs bootstrap/status inspection only. `--duration` bounds the run; Ctrl+C stops it. The runner writes JSON status/suggestion lines to stdout, without sending clicks or calling input executors. It emits an action and board identity, not the complete hand or raw capture. It retains one policy instance, bootstraps historical rows without proposing historical decisions, and deduplicates considered board tokens. It is not a playing loop.

Only fresh timestamped traffic on the active game connection permits a suggestion; capture file modification time and activity on another lobby connection do not count. The default freshness window is two seconds. Invalid/future timestamps, incomplete rows, malformed captures, closed/incomplete game state and unknown own offers block suggestions. Capture replacement/rotation and truncation bootstrap a new reader. Malformed capture faults persist until a new/reset capture; partial final rows can complete normally. After the policy returns, the follower drains capture again and rechecks identity, freshness and board state. Failed decisions do not cause repeated policy calls on the same board.

Offline lifecycle tests cover historical suppression, deduplication, fresh game traffic versus lobby activity, connection closure/reauthentication, capture rotation/truncation, malformed/partial rows, policy errors, slow policies and state changes during evaluation. A real local capture smoke check emitted only `capture_bootstrapped`; that is startup evidence, not validation of new live suggestions. No game launch is needed for these development tests.
