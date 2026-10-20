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
