# Mahjong Soul policy integration

For four-player ATK v0.2 manual suggestions, use `.\MahjongSoulSuggest.bat`. It prints recommended actions only. See [the ATK review](../../games/mahjong_soul/playbook/yonma/ATK.md) for value, yaku, calls, Riichi and defense behavior.

For tile codes and terminal vocabulary, see [the terms reference](../../games/mahjong_soul/TERMS.md).

The shadow and evaluation CLIs now default to `--policy playbook` (manual balanced strategy). See [playbooks](../../games/mahjong_soul/playbook/README.md). Use `--policy efficiency` for the previous pure-efficiency policy. Restart an already running terminal command to load it. `--policy baseline` retains the original integration fixture. Both modes remain read-only.

`policy.Policy` defines `choose(request) -> action`. `proposal_from_policy` gives the policy an independent request copy and wraps its chosen action in the original request/board identity. `evaluate.decide` then re-reads a caller-provided current snapshot and validates the response, including elapsed policy time. This path returns a nonexecutable intent and has no input backend. A future live caller must establish capture freshness separately.

`BaselinePolicy` is an integration fixture: take offered Tsumo/Ron, otherwise discard the exact drawn tile if allowed, otherwise choose a deterministic permitted discard, or Skip an opponent call. It preserves a red five over an ordinary tile when making its deterministic fallback selection. It never selects Chi/Pon/kan/Riichi, computes no shanten and makes no defensive assessment. It is not a trained or strength-tested player.

Run aggregate offline contract evaluation from the Mahjong worktree:

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.evaluate logs/mahjong_soul/capture-20261017-161959-450139.jsonl
```

Use `--schema <path>` to select another schema or `--output <new-path>` to write a new aggregate JSON report. Existing reports are refused. Output contains counts, not hand histories or authentication payloads. Evaluation decodes rows through GameReader, deduplicates identical board tokens, creates requests only for ready own offers, invokes the policy and validates every response. Unsupported offers, malformed rows, unfinished capture rows, game decoding errors, policy failures or zero validated proposals cause a nonzero CLI exit. A closed final connection is reported but does not invalidate earlier offline decisions.

The 2026-10-17 local capture produced 131 requests and 131 validated proposals: 106 discards, 20 skips and 5 Ron choices; no unsupported requests, malformed rows, game decoding errors or policy failures. Captured actions are not changed by proposed decisions, so later recorded states are still the human player's trajectory. These totals measure interface coverage only, not simulated outcomes, agreement, rewards, win rate or policy quality.

The shadow consumer follows live reader state. The separate experimental automatic runner below connects playbook decisions to visual recognition and one persistent input controller.


## Read-only shadow runner

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.shadow --duration 3600
```

Start the process-scoped Steam capture first. The shadow runner follows the newest `capture-*.jsonl` in this worktree, or `--file <path>` pins one capture. `--once` performs bootstrap inspection only; use `--once --verbose` for visible status. `--duration` bounds the run; Ctrl+C stops it. By default the runner prints only readable actions, for example `Discard South Wind`. Add `--json` for full suggestion/analysis JSON or `--verbose` for diagnostic statuses, without sending clicks or calling input executors. It emits an action and board identity, not the complete hand or raw capture. It retains one policy instance, bootstraps historical rows without proposing historical decisions, and deduplicates considered board tokens. It is not a playing loop.

Only fresh timestamped traffic on the active game connection permits a suggestion; capture file modification time and activity on another lobby connection do not count. The default freshness window is two seconds. Invalid/future timestamps, incomplete rows, malformed captures, closed/incomplete game state and unknown own offers block suggestions. Capture replacement/rotation and truncation bootstrap a new reader. Malformed capture faults persist until a new/reset capture; partial final rows can complete normally. After the policy returns, the follower drains capture again and rechecks identity, freshness and board state. Failed decisions do not cause repeated policy calls on the same board.

Offline lifecycle tests cover historical suppression, deduplication, fresh game traffic versus lobby activity, connection closure/reauthentication, capture rotation/truncation, malformed/partial rows, policy errors, slow policies and state changes during evaluation. A real local capture smoke check emitted only `capture_bootstrapped`; that is startup evidence, not validation of new live suggestions. No game launch is needed for these development tests.


Live validation on 2026-10-17: after restarting process-scoped capture and the bounded shadow runner, the new game authenticated and became ready. The follower emitted a nonexecutable BaselinePolicy discard suggestion for 4p at East 1, step 9, generation 1, then suppressed the duplicate board. This confirms new live suggestions, beyond the earlier bootstrap-only smoke test. The previous capture had stopped and the previous one-hour runner had ended; neither should be assumed to persist between sessions. Capture must be active for user-run terminals to receive new suggestions.


## Tile-efficiency policy

`efficiency.EfficiencyPolicy` ranks only current server-permitted discards by lowest shanten, then highest ukeire (unseen copies of tiles that lower shanten), then retaining red fives, then discarding the draw on an otherwise equal tie. Exact red/ordinary tile identities remain distinct actions while both map to the same 34-kind shanten index. It takes offered wins and recommends server-offered Riichi using the best ranked offered tenpai discard; it still declines calls and kans. Riichi is not evaluated for tactical danger or whether remaining undeclared would score better.

Shanten uses the pinned `mahjong==2.0.0` dependency from [MahjongRepository](https://github.com/MahjongRepository/mahjong). Its reduced concealed-hand length accounts for fixed melds; the policy validates that length against the reader's own meld count, including four-tile kans. Seven-pairs and thirteen-orphans patterns are enabled only without fixed melds. Ukeire counts use the pre-discard visible tiles: the tile being discarded remains known, rather than falsely returning to the unseen pool. Three-player analysis excludes 2m through 8m. Missing visibility or inconsistent tile/meld counts reject analysis.

With `--json`, shadow suggestions include the selected discard's `analysis.shanten`, `analysis.ukeire` and improving tile kinds with unseen counts. Unseen copies include tiles possibly held by opponents or in the dead wall; ukeire is not a known live-wall count or draw probability. Tile efficiency does not assess yaku, dora value, opponent danger, furiten, score situation or lookahead beyond the improving draw. Offered wins still rely on server legality.

Tests cover known complete/tenpai regular hands, seven pairs, thirteen orphans, open hands, a fixed closed kan, red-five ties, visible exhaustion, forbidden discards, sanma tile removal and malformed inputs. The 131-board capture replay validated every proposal; of 106 discard choices, 54 differed from baseline and 53 had a strictly better (shanten, negative ukeire) tuple. Cold-cache timing averaged 3.81 ms and peaked at 49.04 ms across those 131 decisions. A second 15-board recording also validated every proposal. These are recorded-state efficiency/contract measurements, not match simulation or strength evidence.

Install new dependencies through the existing Mahjong worktree setup, or `.\.venv\Scripts\python.exe -m pip install -r games/mahjong_soul/setup/requirements.txt`. Balatro's environment is unaffected.

Readable tiles use Man, Pin and Sou: `Discard 1 Man`, `Discard 2 Pin`, `Discard Red 5 Sou`. Riichi prints, for example, `Riichi, then discard 6 Pin`; press Riichi and then discard that exact tile manually. Restart the shadow process to load policy/display changes.


## Completed manual-match review: 2026-10-17

Reviewed the local capture starting at 22:18:51 after the user reported game over. The reader audit confirms match end across ten rounds and 2,253 frames, with no malformed rows, game decode errors, historical state issues, missing action steps or conflicting duplicates. One unrelated lobby schema warning remains separate from game decoding.

Offline replay with the current EfficiencyPolicy validated 164 decision-bearing boards with no rejected proposals or policy errors: 118 ordinary discards, 38 skips, five Riichi recommendations, two Ron and one Tsumo. The recorded player declared Riichi four times and won three hands (two Ron, one Tsumo). These are recorded actions, not attribution to the policy or a win-rate estimate. The capture does not record the version/output of the user's separate shadow terminal.

The five current-policy Riichi recommendations were East 1 step 85 (discard 6 Sou), East 1 step 93 (discard 9 Sou), East 2 step 74 (discard 2 Man), South 1 step 64 (discard 3 Man), and South 1 with one honba step 124 (discard 2 Pin). All ranked offered discards were tenpai. A remaining manual live check is whether the restarted current shadow terminal displays the readable Riichi instruction when an offer appears; no additional native input calibration is needed for that check.

## Playbook strategy

The versioned three/four-player [playbooks](../../games/mahjong_soul/playbook/README.md) now add dora/yakuhai-shape tie-breaks, basic genbutsu defense against Riichi, and configurable Riichi threat handling. This remains a manual-only suggestion pipeline. Run with `--policy playbook`; no automatic input is connected.

Four-player attack is available as `--policy playbook --playstyle atk`; see [ATK.md](../../games/mahjong_soul/playbook/yonma/ATK.md) for exact value, push and Riichi criteria. Balanced stays the default. Three-player attack is not implemented. All playstyles remain manual suggestions only.

## Automatic ATK play and recordings

Run one launcher before opening/reopening Steam Mahjong Soul:

```powershell
.\MahjongSoulAgent.bat
```

This starts process-scoped capture and automatic ATK play together. Approve the Windows capture administrator prompt if shown, then enter a four-player AI room at a physical **1920?1080 client size** and keep Mahjong foreground. No separate capture or shadow terminal is needed. Existing proxy certificate setup is still required; the launcher does not install certificates. Capture is essential: it supplies the live game state.

For manual play with recommendations only:

```powershell
.\MahjongSoulMonitor.bat
```

The monitor starts capture plus the read-only ATK suggestion monitor; it never starts the mouse executor. `MahjongSoulSuggest.bat` is an alias for this monitor package. Use either the agent package or monitor package at a time. For an additional read-only terminal attached to an already running package, run `.\.venv\Scripts\python.exe -u -m agents.mahjong_soul.shadow --policy playbook --playstyle atk` directly.

Both packages bind their worker to their own capture file, wait for capture readiness, and stop their owned processes on Ctrl+C or process exit. If capture fails, the agent is stopped too. Capture console output goes to the adjacent `capture-*.console.log`; launcher startup errors identify that file. `--process` and `--port` configure capture; other options such as `--playstyle balanced` and `--duration 60` go to the worker. `MahjongSoulCapture.bat` remains available for standalone capture diagnostics.

The automatic agent executes **discards, Skip, Riichi, Ron, Tsumo, Chi, Pon and closed/open/added kan** through the native input controller. The ATK policy retains every legal call combination; automatic mode no longer substitutes a discard/Skip just because a call needs a choice panel. For multiple choices, the controller opens the menu once, recognizes the visible tile groups, binds their screen positions to exact contributions (including red fives), and selects the playbook's choice. UI order can differ from server order. The whole visible panel must match the offer in two stable screenshots. Menu opening and selection remain one reserved game step, with matching live server confirmation required before another action.

Chi/Pon action buttons use reviewed visual templates. Kan uses the already reviewed 1080p button layouts for exact operation sets `[1,4]`, `[3,5]`, `[1,6]`, plus an outlined-label presence check in two stable frames. Other offer layouts stop input for inspection rather than guessing a coordinate. Choice recognition currently requires complete upright tile faces (or a unique single representative tile for closed/added kan). Unknown panel rendering, animation or ambiguous tile matches leave screenshots and diagnostics and prevent selection; after the confirmation deadline input stops. These new Kan/choice visual paths have offline regression coverage but await real-panel validation in an automatic run.

Production execution requires captured authentication confirming four seats, three robots and one human player in AI mode. A missing or mismatched room identity blocks input. The standalone `agents.mahjong_soul.auto` module without `--execute` remains read-only.

Every executable run records automatically under `logs/mahjong_soul/sessions/<UTC timestamp>/`:

- `events.jsonl`: decisions and playbook analysis, board snapshots, recognition failures with slot scores, plans, cursor moves, input attempts/delivery failures, server confirmations and run status.
- `frames/`: screenshots linked to reader state and geometry, including preflight, before-input, Riichi/call selection and failure observations.
- `summary.json`: current counts and status; the event log is the source of truth.

The original network capture is referenced by path and stays local. Raw credentials are not copied into agent events. Recordings and network captures remain ignored by Git. The default recording budget is 2 GiB; `--recording-mb` changes it. If durable recording fails or fills, the agent stops input. Cursor parking occurs before hand recognition and after delivery so hovering does not leave the next hand raised. The agent continues observing/recording after an uncertain input, without retrying it.

Inspect the latest run without finding individual screenshots manually:

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.inspect_run
```

Pass a session directory to inspect an older run. The report lists input/confirmation totals and recent failures with sequence numbers and screenshot references. This records issues automatically; it does not run Codex or modify its own source in the background.

Before a discard, every visible concealed tile must match the reader's exact hand multiset, including red fives. Two stable screenshots bind the recommended tile to its actual screen slot. Small rendering shifts are covered by reviewed reference samples; Red 5 Sou uses five-bamboo shape plus red-ink verification. Unknown skins, obscured tiles, animation, changed boards and window geometry prevent input and leave diagnostics. Recognition can retry before delivery as a menu settles; input itself is never retried. Attempted game steps are fsynced before delivery and retained across agent restarts, without reconstructing pending executors.

Skip is recognized visually across supported Chi/Pon/kan offers. Riichi uses the offered tile, verifies the bright eligible tiles against the server offer after opening its menu, then double-clicks the discard and waits for declaration and acceptance. Once Riichi is declared/accepted, decision generation allows only the current drawn tile for ordinary discards. A win requires the matching server offer, visible win button and exact own tile/type confirmation. Combined offers retain their complete operation list.

Capture now publishes an atomic `.jsonl.health.json` heartbeat containing its open connections, exact file identity/length and reader board token. This keeps an idle own turn fresh while proving that capture is still running and agrees with the consumer. `--resume-current` arms a startup board only with matching fresh health; it does not execute old capture history. Restart older capture processes to enable this feature. Capture reset/replacement after an attempted input still stops the agent for inspection.

One controller serializes all stages and verifies matching live server actions or correlated Skip cancellation. Partial delivery, contradictory own action, lost game state and confirmation timeout stop further input. A sent line reports delivery attempt, not acceptance. Unsupported resolutions remain blocked. Opening an AI room and launching the game are still user steps; no computer-use clicks are part of the playing loop.

Offline tests cover the native action paths, staged Riichi acceptance and mismatch refusal, post-Riichi legality, recording failures, single-agent locking, cursor parking and idle-capture proof. Live full-match validation remains required before calling the runner unattended-ready.
