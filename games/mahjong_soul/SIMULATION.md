# Controlled Sanma experiments

The optional offline harness uses [RiichiEnv](https://github.com/smly/RiichiEnv), pinned to 0.4.10. The engine provides three-player East games, legal action masks, North extraction, calls, Riichi and scoring. The runner does not start Steam, capture traffic, or use native mouse input.

## Setup

Use an isolated experiment environment, or install the optional requirements into the Mahjong worktree environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r games/mahjong_soul/setup/simulation-requirements.txt
.\.venv\Scripts\python.exe -m agents.mahjong_soul.simulation --seeds 3 7 --output logs/mahjong_soul/experiments/run-001
```

During development the package was installed with `--target logs/mahjong_soul/simulator-deps`, leaving the normal agent environment unchanged. To use that installation for a command, set `$env:PYTHONPATH = 'logs/mahjong_soul/simulator-deps'` in that experiment terminal first.

Each seed is evaluated at all three candidate seats against the selected fixed opponent profile. Candidate policies start from an identical seeded deal; the runner checks its digest. The default `efficiency` opponents take legal wins, extract North, choose immediate tile efficiency, declare Riichi on the selected legal discard, and pass calls. Additional profiles exercise active calling and different push behavior:

| `--opponents` | Next seat relative to candidate | Other seat | Behavior |
| --- | --- | --- | --- |
| `efficiency` (default) | Efficiency | Efficiency | Immediate efficiency; passes calls. |
| `callers` | East Speed | East Speed | Current call-capable policy, including its defense. |
| `aggressive` | East Speed Push | East Speed Push | Same call-capable policy with always-push enabled. |
| `mixed` | East Speed | East Speed Push | One of each, rotated relative to the candidate seat. |

Each player owns a separate policy instance and public-observation history. No opponent receives simulator hidden hands or wall contents. These opponents share our heuristic implementation; they are neither independent learned references nor Steam AI. Calling them aggressive describes their settings, not proven strength. No client toggle optimization is simulated: every legal call offer reaches the policy.

```powershell
python -m agents.mahjong_soul.simulation --seeds 80 81 82 83 --opponents callers --candidates east_speed east_speed_ready_push --output logs/mahjong_soul/experiments/example-callers
```

Match records include the opponent profile, opponent policy names by absolute seat, and submitted native action counts by player. Integer action keys follow the adapter mapping (2 Pon, 3 Open Kan, 5 Riichi, 8 Closed Kan, 9 Added Kan, 11 Kita). Submitted counts are diagnostics; actual settled calls must be checked in the replay. Comparisons reject pairs with different opponent profiles or seat assignments. Run each opponent profile in a separate output directory; do not pool their outcomes as one opponent distribution.

The engine owns hidden hands and the wall. The policy adapter receives only its public observation, its own hand, legal actions and visible events. Exact physical tile bindings preserve red fives. Riichi is mapped as a two-stage engine declaration followed by its selected discard. Unmapped or illegal choices fail the experiment rather than silently choosing a fallback.

Per-match JSON contains the full offline MJAI replay and outcome metrics. `summary.json` includes seeds, seats, engine version, source revision, adapter/policy hashes, outcomes and timings. Existing experiment summaries are not overwritten. `--single-hand` is for smoke tests only; it is not an East match. `--seats 0` restricts seat coverage for debugging.

Shape-Tenpai speed is the number of own discards until the first engine-calculated zero-Shanten concealed shape in each hand, with open meld count inferred by the engine helper. This does not promise a reachable Yaku or a legal Ron. Hand wins and deal-in hands come from actual engine settlement. Diverging choices change later draws and game length; paired seeds do not imply every subsequent hand remains identical.

## Validation and scope

Tests cover exact red/normal tile mapping, masked opponent hands, deterministic identical seeded replays, and agreement between the engine and our live scorer for a closed Sanma Ron and Tsumo. Twelve full East matches completed across seeds 3 and 7 and all candidate seats. Each candidate finished first twice in six seat assignments; both averaged placement 2.0. This is a plumbing sample, not a statistically meaningful strength comparison. No live policy was changed based on those results.

The engine uses `GameRule.default_mjsoul()` with the standard `3p-red-east` flow. This is not proof of exact parity with every custom Steam room. Special-context value estimates currently use conservative missing-history flags; actual win legality and settlement remain engine-owned. Room extensions, special Yaku variants and complete feature-by-feature parity need further verification. Known unknown discard flags are retained as unknown, not reconstructed from hidden hands.

Next experiments should use many independent seeds and multiple fixed opponent styles, report paired placement/hand-win/speed differences by seed, and preserve a held-out seed set. Choose changes using development seeds; evaluate the frozen candidate on held-out seeds. Repeated seats and hands from one seed are correlated, so raw match counts overstate independent sample size.

## Speed versus folding experiment

`east_speed_push` is an offline diagnostic variant of the current three-player East policy. It changes only `defense.always_push` to true in its own registry. It is not a live playstyle or launcher option. Legal Yaku, action bindings, discard speed ordering, calls and the two fixed efficiency opponents remain otherwise unchanged.

Development seeds are 20, 21, 22 and 23, each tested at all three seats. Held-out seeds are 120, 121, 122 and 123, also at all seats. The candidate definition is frozen before inspecting held-out results. This tests whether suppressing folding helps the requested speed objective; it does not justify removing defense merely because more hands reach Tenpai.

```powershell
python -m agents.mahjong_soul.simulation --seeds 20 21 22 23 --candidates east_speed east_speed_push --output logs/mahjong_soul/experiments/speed-push-development
python -m agents.mahjong_soul.compare_simulation logs/mahjong_soul/experiments/speed-push-development/summary.json
```

The comparison checks matching seed/seat assignments and initial deal digests. It reports first-place rate, average rank, hand-win rate, deal-in rate and shape-Tenpai diagnostics. Exploratory bootstrap intervals resample whole seeds, preserving dependence between seats and hands from one seed. Four seeds per split are a small screening experiment, not reliable evidence of human-level strength or Steam win rate. A variant should not be promoted when its additional Tenpai comes with worse win outcomes and more deal-ins.

Completed screening results: [speed/push review](experiments/SPEED_PUSH_REVIEW.md). The diagnostic variant was not promoted.

## One-step wait-quality experiment

`east_speed_lookahead` is an offline-only candidate enabling `next_wait_tiebreak`. For closed one-Shanten discard options tied on immediate legal-route distance and available improving copies, it compares the expected next-step winning-copy proxy after a useful draw and best next discard. It uses public remaining-copy counts only, checks the entire river for Furiten including exhausted waits, and gives twice the weight to waits supporting Ron plus Tsumo versus Tsumo-only waits. That factor is a heuristic, not a calibrated win probability. Open hands, accepted Riichi and untied immediate-speed choices are unchanged.

The frozen development seeds are 30?33 and the untouched held-out seeds are 130?133, with all three candidate seats and the same fixed efficiency opponents. No production playbook enables the setting. A captured board provides a concrete tie: discarding 7 Sou or 7 Pin keeps one-Shanten with 23 improving copies, while the next-step proxy differs. That demonstrates decision behavior, not a counterfactual hand win.

The strict one-Shanten tie-break produced identical full replays in all 24 pairs across seeds 30?33 and 130?133. It was not promoted: that sample did not expose an actual action change.

A broader frozen candidate, `east_speed_two_draw`, compares total useful-draw-weighted next-wait copies among closed one-Shanten discards within two improving copies of the immediate maximum. It preserves the nearest Shanten, but can trade at most two immediate copies for greater two-draw completion potential. This is a deliberate multi-step speed hypothesis, not a claim that immediate Ukeire is higher. Other policy stages and opponents remain unchanged. Development seeds are 40?43 and held-out seeds are 140?143, across all seats. The two-copy bound and Ron/Tsumo heuristic weight are frozen before evaluation.

Completed lookahead screening: [wait-quality review](experiments/WAIT_QUALITY_REVIEW.md). Neither prototype was promoted. The comparison CLI now reports full-replay divergence so unexercised candidates cannot be mistaken for validated improvements.

## Earlier-hand development experiment

`east_speed_development` is a frozen offline candidate for closed two-/three-Shanten hands. It retains the nearest legal-route Shanten and evaluates at most three discard choices within two immediate improving copies of the maximum. The proxy sums public remaining-copy-weighted next-stage improving copies after a useful draw and best subsequent discard. It is a two-step shape-development heuristic, not a calibrated win probability. Calls and fold handling remain unchanged, and production factories do not enable it.

An exposure screen first tested seed 50 seat 0 (identical replay), then seed 51 seat 0 (different replay). A generated legal Sanma hand also provides a reproducible offensive choice difference at equal 47-copy Ukeire. Development seeds are 50?53, including those inspected screen seeds. Held-out seeds are 150?153, uninspected before freezing the candidate. Both sets cover all three candidate seats. The two-copy margin, three-option bound and scoring formula are fixed before outcome evaluation.

Completed earlier-hand screening: [early-hand review](experiments/EARLY_HAND_REVIEW.md). The proxy changed actual play but was not promoted because no win-rate gain was demonstrated.

## Scored ready-Yaku regression comparison

`east_speed_partial_yaku` is an offline reference retaining the former requirement for an already completed open Yaku in the push gate. Current `east_speed` can instead use exact legal Ron scoring to prove a ready hand's Yaku, including Dragon pair waits. Both retain the same defensive thresholds. Development seeds are 60-63 and held-out seeds are 160-163, all at seats 0, 1 and 2. This is a correctness fix, not a new always-push strategy or evidence of increased win rate.

Completed results and recorded-board findings: [scored ready-Yaku review](experiments/SCORED_READY_YAKU_REVIEW.md). No changed match replays or win-rate gain were observed in this sample.

## Narrow ready-hand push experiment

`east_speed_ready_push` is an offline-only candidate allowing a danger score of 90 for exact-scored Tenpai with at least three available legal Ron copies, while retaining the other push gates. Live East Speed does not set this override. The [fold audit and ready-push review](experiments/READY_PUSH_REVIEW.md) records the inspected boards, frozen development/held-out seed sets, actual action exposure and outcomes. The candidate was not promoted: the two changed held-out matches offset each other in placement and did not demonstrate a win-rate gain.

## Active-opponent evaluation

The [opponent comparison review](experiments/OPPONENT_REVIEW.md) reports 96 completed matches against call-capable and aggressive profiles. The narrow ready-push candidate changed actual play but did not improve wins or placement; held-out caller deal-ins increased. It remains offline-only. Settled replay events verify that the new opponents actually called and declared Riichi.

## Distinct policy intents

The adapter collapses interchangeable physical-copy actions into one exact tile-label/combination intent, retaining the first legal native binding. Red and normal fives remain separate choices. Riichi offers and operation combinations are unique, matching the live contract. This prevents duplicate normal tiles from taking multiple slots in bounded lookahead. The [offense audit and parity probes](experiments/OFFENSE_AUDIT_REVIEW.md) document the correction and its limits; historical bounded-shortlist experiments need re-evaluation before being interpreted as three-distinct-choice tests.

## Single-call counterfactuals

`python -m agents.mahjong_soul.call_counterfactual --seed 80 --seat 2 --called-tile 2z --opponents callers --output <new-directory>` compares one selected Pon against legal Skip. It matches the public decision token, filters the choice before route memory changes, and then resumes the unchanged policy. It checks a single intervention, identical starting deals and the expected replay divergence. This fixed-wall diagnostic is not a win-rate experiment. The [opening South Wind review](experiments/SOUTH_PON_REVIEW.md) found no recovered win or placement gain from Skip and made no live policy change.

## Exhaustive opening-call diagnostics

`python -m agents.mahjong_soul.call_batch --profiles callers aggressive --output <new-directory>` enumerates all non-value first-opening Pon in the existing second-/third-place baseline corpus. It reuses one verified baseline per match and applies each Skip as a separate, guarded intervention. Profiles can run separately in separate output directories. The [full opening-call review](experiments/ALL_OPENING_CALLS_REVIEW.md) defines the corpus and its selection bias; these branches are diagnostics, not an unbiased win-rate benchmark.
