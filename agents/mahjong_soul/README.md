# Mahjong Soul policy integration

For tile codes and terminal vocabulary, see [the terms reference](../../games/mahjong_soul/TERMS.md).

The shadow and evaluation CLIs now default to `--policy efficiency`. Restart an already running terminal command to load it. `--policy baseline` retains the original integration fixture. Both modes remain read-only.

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

Start the process-scoped Steam capture first. The shadow runner follows the newest `capture-*.jsonl` in this worktree, or `--file <path>` pins one capture. `--once` performs bootstrap inspection only; use `--once --verbose` for visible status. `--duration` bounds the run; Ctrl+C stops it. By default the runner writes only JSON suggestion lines to stdout; add `--verbose` to include diagnostic statuses, without sending clicks or calling input executors. It emits an action and board identity, not the complete hand or raw capture. It retains one policy instance, bootstraps historical rows without proposing historical decisions, and deduplicates considered board tokens. It is not a playing loop.

Only fresh timestamped traffic on the active game connection permits a suggestion; capture file modification time and activity on another lobby connection do not count. The default freshness window is two seconds. Invalid/future timestamps, incomplete rows, malformed captures, closed/incomplete game state and unknown own offers block suggestions. Capture replacement/rotation and truncation bootstrap a new reader. Malformed capture faults persist until a new/reset capture; partial final rows can complete normally. After the policy returns, the follower drains capture again and rechecks identity, freshness and board state. Failed decisions do not cause repeated policy calls on the same board.

Offline lifecycle tests cover historical suppression, deduplication, fresh game traffic versus lobby activity, connection closure/reauthentication, capture rotation/truncation, malformed/partial rows, policy errors, slow policies and state changes during evaluation. A real local capture smoke check emitted only `capture_bootstrapped`; that is startup evidence, not validation of new live suggestions. No game launch is needed for these development tests.


Live validation on 2026-10-17: after restarting process-scoped capture and the bounded shadow runner, the new game authenticated and became ready. The follower emitted a nonexecutable BaselinePolicy discard suggestion for 4p at East 1, step 9, generation 1, then suppressed the duplicate board. This confirms new live suggestions, beyond the earlier bootstrap-only smoke test. The previous capture had stopped and the previous one-hour runner had ended; neither should be assumed to persist between sessions. Capture must be active for user-run terminals to receive new suggestions.


## Tile-efficiency policy

`efficiency.EfficiencyPolicy` ranks only current server-permitted discards by lowest shanten, then highest ukeire (unseen copies of tiles that lower shanten), then retaining red fives, then discarding the draw on an otherwise equal tie. Exact red/ordinary tile identities remain distinct actions while both map to the same 34-kind shanten index. It takes offered wins and still declines calls, kans and Riichi decisions.

Shanten uses the pinned `mahjong==2.0.0` dependency from [MahjongRepository](https://github.com/MahjongRepository/mahjong). Its reduced concealed-hand length accounts for fixed melds; the policy validates that length against the reader's own meld count, including four-tile kans. Seven-pairs and thirteen-orphans patterns are enabled only without fixed melds. Ukeire counts use the pre-discard visible tiles: the tile being discarded remains known, rather than falsely returning to the unseen pool. Three-player analysis excludes 2m through 8m. Missing visibility or inconsistent tile/meld counts reject analysis.

Shadow suggestions include the selected discard's `analysis.shanten`, `analysis.ukeire` and improving tile kinds with unseen counts. Unseen copies include tiles possibly held by opponents or in the dead wall; ukeire is not a known live-wall count or draw probability. Tile efficiency does not assess yaku, dora value, opponent danger, furiten, score situation or lookahead beyond the improving draw. Offered wins still rely on server legality.

Tests cover known complete/tenpai regular hands, seven pairs, thirteen orphans, open hands, a fixed closed kan, red-five ties, visible exhaustion, forbidden discards, sanma tile removal and malformed inputs. The 131-board capture replay validated every proposal; of 106 discard choices, 54 differed from baseline and 53 had a strictly better (shanten, negative ukeire) tuple. Cold-cache timing averaged 3.81 ms and peaked at 49.04 ms across those 131 decisions. A second 15-board recording also validated every proposal. These are recorded-state efficiency/contract measurements, not match simulation or strength evidence.

Install new dependencies through the existing Mahjong worktree setup, or `.\.venv\Scripts\python.exe -m pip install -r games/mahjong_soul/setup/requirements.txt`. Balatro's environment is unaffected.
