# Completion-speed model: first diagnostic

This experiment compares a structural Tenpai model with an own-draw-only legal Tsumo model. It is offline only. No production policy, playbook, input executor or terminal output changes.

## Model

`completion_speed.estimate_tenpai_draws` evaluates draw-stage hands at zero, one or two Shanten. It returns expected draws capped at a chosen horizon and probability of reaching structural Tenpai inside that horizon. After each useful draw it considers every discard reducing Shanten and chooses the lowest remaining capped cost. Blocked branches retain their full remaining cost; they are not omitted from the average. Useful draws reduce public unseen counts. A state budget returns an explicit unavailable result rather than a partial estimate.

Unhelpful draws are returned to the pool. The denominator includes unknown opponent holdings, not just live-wall tiles. Opponent actions, future calls, equal-Shanten shape changes, Yaku, Furiten, Riichi decisions and winning-tile availability are excluded. The probability is exact only inside this simplified replacement model. It is neither a calibrated real-game probability nor an expected win time. Public unavailable copies are never restored by discarding or calling.

The legal Tsumo variant uses the existing exact scorer for every terminal wait. It grants no hypothetical Riichi or situational Yaku, and counts only available legal self-draw copies. Furiten does not block Tsumo. In this variant a structural ready hand with no legal Tsumo waits is blocked rather than counted as success. Red fives are canonicalized for legality only; the model does not estimate hand value. Fixed melds, round/seat winds and open-Tanyao rules remain part of scoring.

This is still not a complete expected-win model: Ron, future calls and equal-Shanten repairs are excluded. In particular an open no-Yaku Tenpai may be repairable in reality but is blocked in this model. That can systematically penalize opening. The Pon branch uses the current policy's selected post-call discard; it does not optimize every alternative post-call discard under this new model. These omissions must be addressed or evaluated before any production use.

## Recorded opening probes

The two public requests from the recovered 3 Pin Pon cases were evaluated at a 12-own-draw horizon:

| Choice | Starting Shanten | Capped draws to structural Tenpai | Model Tenpai probability |
| --- | --- | --- | --- |
| Skip | 2 | 7.091 | 78.89% |
| Pon, discard 9 Man | 1 | 5.558 | 87.05% |

| Choice | Capped draws to legal Tsumo | Model Tsumo probability |
| --- | --- | --- |
| Skip | 11.066 | 26.21% |
| Pon, discard 9 Man | 11.746 | 6.23% |

The inputs have different board tokens but the same concealed hand and relevant public availability, so these are not independent model examples. Both produce the same estimate. The first structural-only cold probe took about 0.14 seconds; the second benefited from the existing global Shanten cache. These are diagnostic timings, not a live latency guarantee.

The prior full-match counterfactual recovered wins by skipping these calls. The structural model still prefers Pon, while the legal Tsumo model prefers Skip. Therefore structural waiting-time alone does **not** explain the observed call problem, but legal completion exposes an important difference. The recorded win does not itself establish Skip's expected superiority either. This is diagnostic agreement on inspected cases, not independent evidence of strength. No live change or strength improvement is claimed.

[Machine-readable probes](completion_speed_probe.json) preserve the public board tokens, actions, estimates and timings.

## Complete 28-call diagnostic

All 28 public calls were evaluated after exactly reproducing 22 saved baseline matches. They represent 21 unique public board tokens, not 28 independent situations. Both branches were supported for 24 calls; four involved an unsupported three-Shanten state. No state-budget failures occurred.

| Opponents | Legal model favors Skip | Favors Pon | Comparison unavailable |
| --- | --- | --- | --- |
| Call-capable | 4 | 7 | 3 |
| Aggressive | 6 | 7 | 1 |

The model prefers Skip in both previously recovered-win contexts under both profiles. It also prefers Skip in six other profile-specific cases where the prior fixed-deal intervention left target-hand win status unchanged. None of this establishes a prospective policy improvement: these cases were already inspected and baseline first-place games are excluded. Model preferences were **not** applied in these reruns; this is baseline reproduction plus public-state analysis, not a new tournament.

[Full all-case report](completion_speed_all.json) contains source hashes, exact replay confirmations and explicit unsupported results. Maximum observed model evaluation time was about 0.45 seconds in this small corpus; it excludes replay generation and is not a general bound.

## Verification and next step

Analytic tests cover a geometric waiting-time case, exhausted progress, useful-draw depletion, a ready hand, bounded search failure, invalid availability and immutable recorded requests. Structural results explicitly mark legal-win evaluation false. Further tests check no-Yaku blocking, legal Yakuhai waits, Furiten allowing Tsumo, and the preference reversal in the recorded case. The batch refuses altered baseline replays, missing public targets and existing output files. All 833 Mahjong tests passed with the pinned optional simulator dependencies available.

Next is accounting for equal-Shanten repairs of unsecured open hands and Ron opportunities. Only then should the model become an offline call candidate and face fresh full-match evaluation. Do not enable either simplified estimate as a live call rule.

Reproduce from the repository root:

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.compare_completion_speed tests/mahjong_soul/fixtures/call_width.json --output logs/mahjong_soul/completion-speed-new.json
```

The command refuses to overwrite an existing output.

To re-evaluate every opening from the existing diagnostic corpus (requires the pinned optional simulator dependencies and local source replays):

```powershell
$env:PYTHONPATH = 'logs/mahjong_soul/simulator-deps'
.\.venv\Scripts\python.exe -m agents.mahjong_soul.completion_batch --output logs/mahjong_soul/completion-speed-all-new.json
```

This reruns baselines only, never gameplay input or the live agent. Every full replay must exactly match its saved baseline before a public request is evaluated. Three-Shanten states are explicitly unavailable; a comparison requires both branches to be available. The output records frozen source hashes and incremental completion status; incomplete runs must not be presented as all-case results.

The bounded ready-repair and Ron-sensitivity follow-up is documented in [Completion scenarios](COMPLETION_SCENARIOS_REVIEW.md).
