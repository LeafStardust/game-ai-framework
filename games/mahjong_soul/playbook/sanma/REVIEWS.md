# Three-Player Playbook Reviews

## 2026-10-20: Three-Player East Speed

Session: `20261020T060105-596741Z`, source revision `01c91ca6`. Own absolute seat: 1. Final scores were 26,100 / 41,000 / 37,900: first place. Thirty decisions were confirmed, including one Riichi, one five-Han Ron and two North extractions. The 31 input deliveries include the two-stage Riichi action. No action failure or crash was recorded. Visual preflight retries recovered; no threshold was relaxed for animation frames.

### Declined calls

- Sequence 120, East One: Pon of 9 Sou changed the nearest supported legal-Yaku route from two-Shanten to three-Shanten. The generic triplet improvement did not preserve the closed Riichi route. Skipping was consistent with speed-first play.
- Sequence 371, East Two: Pon of 9 Pin changed the nearest supported legal-Yaku route from one-Shanten to two-Shanten. The policy rejected a slower open route. No Chi was proposed.

### East Two deal-in

At sequence 574, discarding 6 Pin or 9 Pin kept one-Shanten with fourteen available improving copies and equal projected Han. Seat 0 had declared Riichi and had already discarded 9 Pin. The agent selected 9 Pin as Genbutsu against that threat. Seat 2, with an open East triplet, instead won on 9 Pin for 2,600 points.

This is a multi-opponent danger-model limitation, not proof of an incorrect winning-progress calculation. The current threat model does not treat one exposed Yakuhai triplet as confirmed Tenpai; the hidden hand was not known at decision time. Discarding 6 Pin would have exposed the hand to the Riichi player. No hindsight-based exception, blanket fold, or unsupported claim of a better alternative was introduced.

### Execution and validation

Both North extractions used the ordinary `[discard, extract_north]` offer. The combined Kita-plus-Kan layout was not encountered, so its live confirmation remains pending. Offline replay validated all thirty decisions and reproduced all thirty selections without policy errors.

No strategy settings changed following this review. Next validation is another normally played three-player East AI match with recording enabled; no manufactured hand is required. A combined Kita-plus-Kan offer, if encountered, will provide the remaining input-layout check.


## 2026-10-20: Second East match

Session: `20261020T062747-902083Z`, source revision `e7026c24`. Own seat 2 finished second at 30,000 points, without wins or deal-ins. One Riichi deposit and a 4,000-point Tsumo payment account for the loss from 35,000. Thirty-seven actions were confirmed; an unsubmitted Skip expired as the round ended. No North offer occurred.

Six of the seven Pon decisions remained consistent with legal-Yaku progress or defense checks. At sequence 577, however, the Green Dragon Pon advanced one-Shanten to Tenpai with four available winning copies, nine wall tiles, relative danger 46.8 and average known Ron value 1,150. A hard-coded 2,000-point ready-hand floor wrongly rejected it for this speed-first playbook. Version 0.4 makes the threshold configurable and uses 1,000 for Three-Player East Speed only.

The later 2 Pin Pon at sequence 818 still requires a discard with relative danger 90, above the configured 85 limit, and remains rejected. The final Riichi at sequence 837 discards 2 Pin safely against the existing Riichi threat, keeps four waiting copies (White/Red Dragon), and increases known average Ron value from 2,000 to 3,900. It remains accepted. Opponent Tsumo afterward does not invalidate that choice by itself.

Offline replay validates all thirty-eight recorded decisions. Exactly one recommendation changes: the Green Dragon Pon replaces the rejected call. These are fixed-board comparisons, not a simulation of how the call would alter the rest of the round.


## 2026-10-20: Third East match and result controls

Session `20261020T064806-180747Z`, revision `90501c8e`: own seat 0 finished second at 40,700 (opponents 15,700 and 48,600). Sixty-five game actions were confirmed, including seven native North extractions, two Riichi declarations and one Ron. One Skip was not submitted before the round ended. Most preflight failures were loss of foreground-game focus, not policy failures.

The disputed first-round 3 Pin Pon (sequences 344/404) has a raw Tenpai discard of 4 Pin, but the resulting hand has no Yaku. It contains a called 3 Pin triplet, 2 Sou triplet, 7-8-9 Sou sequence, 2 Pin pair and 7/9 Pin waiting for 8 Pin: neither All Simples nor another Yaku is present. The policy correctly declines this opening. North/Dora bonuses cannot supply its missing Yaku.

Recorded first-round 9 Pin alternatives had fewer available improving copies or greater distance than the selected action. In the later first-round repeat (sequence 1061), Riichi on 5 Pin retains five winning copies, versus three after discarding 9 Pin. Speed-first selection favors the former; the result alone does not establish that a different discard was better.

The result-screen recorder skipped later UI frames because game-state tokens no longer changed after a round ended. Recording now continues during result states. A separate guarded Continue/Confirm handler uses Windows English OCR, known ended-round state, visible result context, two stable frames, current geometry/state rechecks and a one-click latch. It never starts another match. Windows OCR was smoke-tested on a real saved game screenshot. Actual result-button screen validation is pending the next recorded match.


## 2026-10-20: Fourth East match and result-control fixes

Session `20261020T104017-336368Z`, revision `4324eb7d`: own seat 2 finished second at 25,100, behind 65,100 and ahead of 14,800. Fifty-four gameplay decisions were confirmed, including three North extractions, two Pon, three Riichi and a five-Han Ron shared with another winner. Two later deal-ins cost 12,200 and 7,700 points. No gameplay action failed or crashed.

No Continue/Confirm click was delivered. The result path incorrectly reused gameplay freshness checks during intentionally idle result states; OCR output also contained control characters that broke JSON decoding. The fixes use source-checked result snapshots, sanitize OCR text with explicit UTF-8 transport, and match displayed score values when stylized result headings are missed. Actual round and final Confirm crops/OCR words are regression fixtures. Gameplay freshness checks are unchanged. Another recorded game is required to confirm real post-round native delivery after this correction.

## 2026-10-20: Fifth East match

Session `20261020T110201-036825Z`, revision `d36dbba6`: own seat 2 finished second at 32,700, behind 40,400 and ahead of 31,900. All 53 gameplay decisions were confirmed, including five North extractions, one Pon, one Open Kan, one Riichi and one Ron. There were no gameplay action failures or deal-ins. The 1,000-point Riichi deposit, 4,800-point Ron gain and 6,100-point opponent Tsumo payment explain the final score.

No automatic Continue/Confirm delivery was recorded. The previous idle-state/OCR exceptions did not recur. Saved frames 572 and 573 both recognize Confirm at (1779, 1002), with zero difference in the checked label crop; offline OCR took approximately 1.2 seconds per frame. Thus label recognition and crop stability alone do not explain the withheld click. The final geometry/state checks or intervening screen progression require explicit rejection tracing before changing input safeguards. Result-button native delivery remains unverified. The combined Kita-plus-Kan layout was not offered in this game.

No strategy parameters changed based on this result. Next work is to trace result-button rejection reasons and reduce unnecessary recognition delay while preserving current-screen validation; another manufactured hand is not required.

## 2026-10-20: Sixth East match and first confirmed result click

Session `20261020T111649-661122Z`: own seat 0 finished second at 32,100, behind seat 2 at 44,100 and ahead of seat 1 at 28,800. All 47 gameplay decisions were confirmed: 34 discards, four Skips, four Pon, three North extractions, one Riichi and one Tsumo. There were 49 input deliveries because some actions have multiple input stages. No action failure, error or halt was recorded. Preflight retries for animation, recognition and foreground geometry recovered.

Seat 0 paid a 5,200-point Ron in the first round, won a two-Han Tsumo for 2,000 total in the second, and paid a 3,900-point Ron in the last. Its first-round 1,000-point Riichi deposit accounts for the remaining difference from 35,000. The third-round 1,300-point Ron was between the other two players. No policy adjustment is justified by these results alone; execution confirmation is not evidence that every strategy choice is optimal.

The post-round Confirm at sequence 400 was delivered at sequence 403 and confirmed by advancing game state at sequence 408. This is the first recorded live native result-button progression after the latency fix. The final detected Confirm was withheld with `window_changed_after_ocr` at sequence 1142, showing that the foreground guard and new rejection diagnostics work. Final-screen Confirm delivery and the combined Kita-plus-Kan layout remain unverified. Next validation can use an ordinary recorded game with the game foreground through the result screens.

## 2026-10-20: Eighth recorded East session

Session `20261020T120330-675251Z`, revision `87f5fe3a`: own seat 2 finished second at 35,600 (opponents 43,900 and 25,500). All 122 gameplay decisions were confirmed: 98 discards, nine Skips, seven North extractions, five Pon, two Ron and one Open Kan. No action errors, halts or timeout retries occurred, so the new timeout recovery was not exercised live. Two exhaustive draws cost 2,000 each; Ron wins gained 2,600 and 2,000. No deal-ins occurred.

Seven round-result Confirm clicks were delivered, with six confirmed by a following round. The final delivery cannot be confirmed by a new-round event after match end. Final-results Confirm remains a separate validation item.

No assist switch clicks were attempted. Offline recognition of actual gameplay frames reproduced the failure: collapsed glyph masks were calibrated from a dimmed result overlay, and their brighter antialiased gameplay edges failed the silhouette threshold. Added actual gameplay glyph variants without lowering that threshold, retaining both appearances as regression fixtures. Native switch delivery still requires live validation. No strategy parameters changed based on this result.

## 2026-10-20: Ninth recorded East session

Session `20261020T122443-992610Z`: own seat 1 finished second at 38,300 (opponents 53,900 and 12,800). Eight collapsed assist changes were delivered and visually confirmed, including Auto Win, Skip Calls on/off and accepted-Riichi Auto Discard. Three round Confirm clicks were delivered and confirmed. Client Auto Win completed a Tsumo and the last Ron; delegated actions are not all counted as controller confirmations.

A final Riichi menu failed visual preflight: the server allowed `0p`, `1p`, `7p`, while the client also highlighted normal `5p`. The server encodes the Five Pin discard kind using the red variant, while the client highlights both physical variants. Comparing exact labels wrongly rejected that valid menu. Recognition and final execution now compare allowed tile kinds with red/normal fives normalized; the exact selected physical tile must still be visibly bright. Actual sampled menu faces are a regression fixture. The eventual observed Riichi discarded 7 Pin instead of the planned Red Five Pin, correctly triggering the contradictory-action guard; the log does not establish who selected that alternative. No change to that guard or strategy parameters was made.

## 2026-10-20: Tenth recorded East session

Session `20261020T124308-369100Z`: own seat 2 finished second at 32,800 (opponents 53,300 and 18,900), with no wins or deal-ins. Its Riichi deposit and exhaustive-draw Tenpai payment offset each other; a later opponent Tsumo cost 2,200. Forty-eight native gameplay decisions were confirmed out of forty-nine suggestions; the controller finished idle without errors, retries or halts. Suggestions delegated to client assists do not require separate native execution.

All nine assist changes were visually confirmed. Riichi selection on 6 Sou completed, with no allowed-highlight mismatch. This menu had only 6 Sou available, so the specific red/normal Five mismatch fix was not exercised live. Five result Confirm clicks were delivered: three subsequent rounds supplied network progression confirmations, while the last round-score and final-results buttons have no following round. The final-results click at sequence 1307 was followed by the saved room-screen frame 1314, providing visual evidence of final-screen progression.

No implementation or strategy parameters changed after this review. Ordinary recorded play can continue on the current revision; no restart is needed for this documentation-only commit. Remaining coverage includes the mixed red/normal Five Riichi menu, a real timeout recovery, and combined Kita-plus-Kan offers.

## Strategy audit: call suppression before accepted Riichi

Reviewed decisions and call-rejection diagnostics across the recent East sessions from `20261020T104017-336368Z` through `20261020T124308-369100Z`. No recorded selection in that set chose zero-copy Tenpai; that potential defect was not observed. The larger recent games include genuine Pon and Ron wins, so a blanket refusal to call or accept wins does not explain the results.

A concrete winning-progress problem was introduced by client assist preferences. In session `20261020T122443-992610Z`, East One repeat one, Skip Calls was enabled before accepted Riichi. At captured step 27 an opponent discarded White Dragon while the agent held two White Dragons. Reconstructing the legal Pon candidate on that board yields a policy-accepted two-Han route from one-Shanten to Tenpai. The concealed hand was `4s 9p 9s 1m 5p 5z 1m 4p 2s 3s 9s 5z 1m`. The toggle hid the opportunity before the policy could evaluate it. The candidate is a local reconstruction, not a captured server offer or proof that a call would have won the round.

Skip Calls now stays off for every provisional closed route and is enabled only after accepted Riichi. This preserves future call evaluation rather than changing call thresholds indiscriminately. The recorded board and reconstructed candidate are regression coverage. An apparent Green Dragon candidate in the following round was excluded from the finding because the UI resets assists at round start; carrying toggle state across that boundary would overstate suppressed opportunities.

This correction addresses a demonstrated missed Tenpai opportunity. It does not establish a stronger match win rate; ordinary recorded games must measure its practical effect. No increased aggression, reduced Yaku checks, or result-based policy threshold changes were introduced.

## Speed-priority call review

The shared same-distance call logic applied a value-gain gate before East Speed's separate speed check. A lower-Han call could therefore be rejected even when it retained legal winning distance and increased improving copies. East Speed now bypasses that value gate; its existing legal-Yaku, distance, available-copy and push/fold checks remain. Four-Player East Speed is version 0.2 and Three-Player East Speed is version 0.5. South Attack behavior is unchanged.

A focused decision-layer regression tests a one-Han call with eight improving copies against a four-Han closed route with four copies at equal distance, and rejects the call when it adds no copies. Replaying recorded Skip decisions from recent sessions did not yield a changed selection for this correction. This is enforcement of the requested speed ordering, not a measured win-rate gain or proof of an additional missed call in those games.
