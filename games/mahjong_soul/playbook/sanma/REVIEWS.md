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
