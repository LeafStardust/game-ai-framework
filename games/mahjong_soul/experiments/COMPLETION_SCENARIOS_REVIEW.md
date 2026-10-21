# Completion scenarios: ready-hand repairs and Ron

The offline completion model now allows one equal-Shanten change **after reaching Tenpai**, including a change that turns a no-Yaku hand into a legal winning hand. It also evaluates explicit Ron sensitivity scenarios. The production playbooks, terminal suggestions and live input behavior are unchanged.

## What changed

The previous model froze a ready hand, so an open no-Yaku ready hand could never recover. The new search considers a draw and discard that preserves Tenpai and strictly improves one-cycle legal completion chance. It evaluates every qualifying discard, allows the original hand to be kept instead, and permits at most one such repair along a forecast path. Accepted or declared Riichi disables repairs. Non-ready equal-Shanten improvements are still excluded; this is not exhaustive hand development.

Legal Tsumo and Dama Ron waits use the existing complete-hand scorer. The search tracks deliberately chosen discards, including the immediate post-Pon discard, for permanent Furiten. A discarded structural waiting tile blocks all Ron waits even if that discarded wait has no available copies. Known Furiten blocks Ron without blocking Tsumo. No new Riichi or situational Yaku are granted. Existing accepted Riichi remains part of scoring.

Exact wait legality is cached by retained hand shape. Public unseen counts and the full structural-wait Furiten check are applied separately to each search state. Four retained fives use a valid physical red-five allocation. Cost ties within 12 decimal places prefer higher model completion probability, avoiding arbitrary choices from roundoff.

## Ron scenarios and assumptions

The horizon is twelve abstract own-turn cycles. Each cycle offers hypothetical opponent exposures followed by an own draw. For each opponent, the scenario assumes a uniform tile from the public unknown pool is exposed with probability `ron_rate`. This is a sensitivity parameter, **not an estimate of opponent play**.

Four settings are evaluated:

| Setting | Ready repairs | Assumed exposure rate per opponent |
| --- | --- | --- |
| No repairs | 0 | 0 |
| Repairs | 1 | 0 |
| Repairs + half exposure | 1 | 0.5 |
| Repairs + full exposure | 1 | 1 |

Useful own draws reduce the unknown pool. Unchanged-hand failures return their tile to the pool, as in the prior replacement model. Because those hypothetical Tsumogiri tiles are not individually tracked, any such failure conservatively disables all future Ron in that forecast branch. The search never silently assumes those discards cannot cause Furiten. Known Furiten is also retained conservatively rather than predicting when temporary Furiten will clear.

This model does not predict opponents' hands or discards, future calls, Kan, North extraction, defense, future Riichi, or actual remaining wall exhaustion. The public unknown pool includes opponents' concealed tiles. Its probabilities are only probabilities inside these stated assumptions; they are not real-game win odds. Its cycle cost is capped at the horizon, not an uncensored expected win time. The fixed Pon branch uses the current policy's selected post-call discard, rather than optimizing every alternative call plan.

## Reproducible corpus

The capture command reproduces every saved baseline exactly and saves only each selected decision's own-hand/public request. This reusable local file removes the need to rerun full baseline matches for every future model iteration. A second command evaluates the four scenarios against those snapshots. Both commands preserve existing output files; incomplete evaluation reports remain explicitly marked incomplete. Unsupported three-Shanten branches and state-budget failures never count as votes for either action.

```powershell
$env:PYTHONPATH = 'logs/mahjong_soul/simulator-deps'
.\.venv\Scripts\python.exe -m agents.mahjong_soul.completion_scenario_batch capture --output logs/mahjong_soul/public-calls-new.json
.\.venv\Scripts\python.exe -m agents.mahjong_soul.completion_scenario_batch evaluate logs/mahjong_soul/public-calls-new.json --output logs/mahjong_soul/scenarios-new.json
```

Capture requires pinned RiichiEnv 0.4.10 and the existing local replay corpus. Model evaluation itself does not need RiichiEnv. Neither command launches the game or sends inputs. The result records source hashes and a SHA-256 of the public request corpus.

## Complete diagnostic results

All 28 public requests were captured after 22 exactly reproduced baseline matches. They represent 21 unique board tokens. Every scenario preferred Skip in ten cases and Pon in fourteen; four comparisons were unsupported because one or both branches began at three Shanten. No state-budget failure occurred in this corpus. The seven unsupported individual branches belong to those four comparisons and must not be counted as seven independent cases.

Ready repairs and Ron sensitivity changed the numeric forecasts, but **none changed the action preference** on this inspected set. For the recovered 3 Pin opening, the repaired own-draw-only model raises Pon's completion probability from about 6.23% to 15.95%, while Skip remains ahead at about 28.45%. These are model probabilities, not real-game win rates. Diagnostic agreement is not fresh strength evidence.

[Full scenario results](completion_scenarios.json) and [reusable public requests](completion_scenario_requests.json) preserve all cases and source provenance. Evaluate the tracked request file directly to reproduce the model results without running baseline matches again:

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.completion_scenario_batch evaluate games/mahjong_soul/experiments/completion_scenario_requests.json --output logs/mahjong_soul/scenarios-reproduced.json
```

All four settings and both branches took about 28.4 seconds in total; the slowest request took about 9.18 seconds across all settings. Those timings include cache effects and do not establish live decision latency.

## Fresh candidate evaluation plan

`east_speed_completion` is enabled only by the offline simulator. No production playbook factory sets `completion_opening_guard`. It evaluates first Pon openings from raw two Shanten into an unsecured one-Shanten route. It rejects a call only when both bounded forecasts are available and Skip has strictly lower twelve-cycle capped cost. It uses one ready repair, zero assumed Ron exposure, a 5,000-state budget and a numerical cost tolerance of 1e-10. These settings are frozen before fresh outcomes are inspected. Other existing call and defense gates stay in place; immediate Tenpai, already secured Yaku and later calls are outside this new filter. After rejecting a candidate, the policy may retain another valid call rather than indiscriminately skipping all offers.

The separate diagnostic scenarios showed the same preferences with and without the Ron assumptions, so the candidate uses the own-draw setting instead of fitting an opponent discard rate. Unsupported forecasts preserve the existing decision. This remains an experimental hypothesis, including its selective-depletion approximation and omitted non-ready shape improvements.

Fresh development seeds are 400-403; held-out seeds are 500-503. All three seats, both candidate/current policies and caller/aggressive opponent profiles give 96 full East matches. Compare actual replay differences, hand wins, deal-ins and final placement separately by profile and split. The four-seed clusters are small, seats and opponent profiles are correlated, and the opponents share the same heuristic family. No human, Steam AI or independent trained-engine strength claim follows from this screen. Timing under concurrent runs must not be presented as a controlled performance benchmark.

## Verification

The focused tests cover repair of no-Yaku Tenpai, accepted Riichi preventing changes, an analytic single-cycle Ron calculation, conservative Ron blocking after an untracked miss, Furiten with an exhausted structural wait, chosen repair discards causing Furiten, zero-extension agreement on optimal capped Tsumo cost, input validation and explicit state-budget failures. Batch tests cover immutable public requests, the post-call discard river, missing legal actions, duplicate/unverified/incomplete sources, preservation of existing files and interruption reporting.

All 861 Mahjong tests passed with the pinned optional simulator installed. These checks establish implementation behavior, not playing strength.
