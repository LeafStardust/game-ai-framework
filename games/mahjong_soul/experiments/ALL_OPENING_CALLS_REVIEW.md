# All non-value opening calls in the losing-match corpus

## Complete diagnostic scope

The existing active-opponent corpus has 48 baseline matches: seeds 80-83 and 180-183, all three candidate seats, against caller and aggressive profiles. Thirty-four baseline matches finished second or third. Scanning every settled call in those matches identified 28 non-value opening Pon across 22 matches: fourteen calls per opponent profile. The manifest was fixed before running any new counterfactual outcomes. This is the full eligible set in that corpus, not a sample chosen for favorable Skip results.

An eligible call is the candidate's first open meld in its hand, is a Pon, and calls a tile that is neither a Dragon nor the current round/seat Wind. A preceding Closed Kan does not make the hand open. Value calls and later calls after an opening are excluded. Red called tiles and red tiles consumed from the hand retain their exact labels. Eligibility is read from public meld and round events; it does not inspect hidden wall contents or opponents' hands.

## Method

The batch reruns each included baseline match once and requires its entire MJAI replay to match the existing reference. It traces chosen calls using public policy requests, then matches every eligible settled call to exactly one traced request. Each counterfactual changes only that decision to legal Skip before route memory updates. It requires the first changed replay event to be the exact Pon event index in the original replay. All later actions use the normal policy. Baselines are reused across multiple calls in the same match; interventions are separate branches, never cumulative skips.

Complete local replays, public target requests, analysis and source hashes are retained under `logs/mahjong_soul/experiments/nonvalue-openings-{callers,aggressive}`. The batch writes a fixed manifest and incremental summaries; a partial run is explicitly incomplete. Changed baselines, unmatched calls or earlier/unrelated intervention effects stop the run rather than being silently counted.

The full Mahjong suite passed 809 tests, including batch coverage, correct value Winds, Red Five identity, baseline reuse and rejection of invalid/incomplete comparisons. No live agent or native input was started.

## Interpretation limits

This is a postselected losing-match diagnostic, not an unbiased policy tournament. Baseline first-place games are intentionally outside this question, so a rule that improves these calls could still harm excluded winning games. Different calls in one match reuse its baseline and wall; opponent profiles also reuse seed sets. Per-call branches are correlated and must not be counted as independent match samples. Former development/held-out labels identify the source corpus only; all of these seeds are now inspected diagnostic data.

Counterfactual draws and later game length diverge after the intervention. Report the targeted hand separately from match placement and final points. A recovered target-hand win is a concrete counterexample on that hidden deal, not proof that Skip has higher expected value from public information. Any general call rule needs fresh, balanced development and held-out matches before enabling it live.

## Complete results

All 28 call interventions completed, using 22 exactly reproduced baselines and 28 Skip branches: fifty full matches. Both profile batches are marked complete, with no unmatched targets or earlier replay divergence. The cases represent 21 distinct public board tokens; shared states across opponent profiles are not independent samples. [Complete data](all_nonvalue_openings.json) includes every case, both outcomes and source hashes.

| Opponents | Calls compared | Target-hand wins recovered by Skip | Target-hand wins lost by Skip | Placement improved | Placement worsened |
| --- | --- | --- | --- | --- | --- |
| Call-capable | 14 | 2 | 0 | 2 | 0 |
| Aggressive | 14 | 2 | 0 | 2 | 0 |

The recovered wins are the 3 Pin opening at seed 80 seat 1 hand index 1, and seed 81 seat 1 hand index 0, under both opponent profiles. Both start from two-Shanten and 40 improving copies, then Pon into an unsecured Tanyao route at one-Shanten with only seven improving copies. Neither has secured Yaku after the post-call discard. Skip recovers a win and changes second place to first in each of these fixed-deal probes.

All other interventions leave target-hand win status unchanged. This does not mean their scores, deal-ins or later trajectories are equal, and it does not establish that skipping every opening is good. In particular, other calls reach legal Tenpai, secure Yaku or maintain substantially broader improving-tile availability.

## Targeted follow-up

The diagnostic pattern supports testing a narrow hypothesis: for an initial opening from two-Shanten into an unsecured one-Shanten route, require at least eight available improving copies. Preserve immediate Tenpai, already secured Yaku, later calls and all existing defensive gates. Eight is an experimental cutoff selected from this diagnostic set, not a derived universal optimal threshold.

That candidate must be evaluated separately on fresh, balanced matches including baseline first places. Development seeds are 200-203 and held-out seeds are 300-303, all three seats against both caller and aggressive profiles, with no threshold tuning after outcomes are inspected. The live policy is unchanged during that evaluation. The completed exhaustive audit itself makes no production playbook change.
