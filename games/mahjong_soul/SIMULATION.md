# Controlled Sanma experiments

The optional offline harness uses [RiichiEnv](https://github.com/smly/RiichiEnv), pinned to 0.4.10. The engine provides three-player East games, legal action masks, North extraction, calls, Riichi and scoring. The runner does not start Steam, capture traffic, or use native mouse input.

## Setup

Use an isolated experiment environment, or install the optional requirements into the Mahjong worktree environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r games/mahjong_soul/setup/simulation-requirements.txt
.\.venv\Scripts\python.exe -m agents.mahjong_soul.simulation --seeds 3 7 --output logs/mahjong_soul/experiments/run-001
```

During development the package was installed with `--target logs/mahjong_soul/simulator-deps`, leaving the normal agent environment unchanged. To use that installation for a command, set `$env:PYTHONPATH = 'logs/mahjong_soul/simulator-deps'` in that experiment terminal first.

Each seed is evaluated at all three candidate seats against two fixed efficiency opponents. Both `efficiency` and `east_speed` candidates start from an identical seeded deal; the runner checks its digest. Opponents take legal wins, extract North, choose immediate tile efficiency, declare Riichi on the selected legal discard, and pass calls. They are a deterministic baseline, not the Steam AI or a strong learned opponent. No client toggle optimization is simulated: every legal call offer reaches the policy.

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
