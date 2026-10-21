# v0.7 second follow-up: recorded policy and UI fixes

Session `20261021T115221-159346Z`, source revision `3a561f97`.
Both authenticated Three-Player East AI matches completed:

| Match | Rank | Final score | Hand wins | Deal-ins |
| --- | --- | --- | --- | --- |
| 1 | 1 | 77,800 | 5 / 7 | 0 |
| 2 | 1 | 75,600 | 3 / 4 | 0 |

All 127 controller actions were confirmed. No blocked/error journal rows.
The prior cross-round assist fix was exercised: one obsolete assist request was
superseded without halting. However, 148 preflight failures and 12 waiting-visual
rows show recognition problems remained. These wins do not excuse those failures
or establish general playing strength.

## Thirteen Orphans

Decision 3340 recommended Riichi discarding 6 Sou. The exact scored wait was
1 Man with two unseen copies, worth 32,000 both with and without Riichi.
The generic Dama preference required a minimum wait width, so this narrow
Yakuman wait bypassed it. The hand subsequently won Thirteen Orphans by Tsumo.

The policy now excludes scored Thirteen Orphans (including the thirteen-sided
variant) from Riichi regardless of wait width, and preserves the selected
Thirteen Orphans ready hand rather than declaring on a different discard.
This restriction uses actual scored Dama Yaku, not an aspirational route label.
Ordinary Riichi criteria are unchanged. The recorded decision is a regression
fixture expecting a plain 6 Sou discard and the same 32,000-point Dama wait.

## Native recognition

The Pon / Kan / Skip offer in frame 0001296 positions Pon at (730,835), which
was absent from ordinary call scanning. The old nearest sample also missed the
confidence threshold. Added this reviewed position and a sample from the visible
blue Pon label. A cropped screenshot regression proves Pon is recognized while
Chi, Skip and North extraction are rejected on that same crop.

The Red Five Sou in frame 0003157 repeatedly failed classification (nearest
existing sample distance 10.9, threshold 10). The screenshot visibly confirms
the red bamboo five in the separated drawn-tile slot. Added its reviewed sample;
a regression recognizes it without using the reader's expected identity.
Recognition thresholds and preflight stability checks are unchanged.

Thirty-two failures required the foreground 1920x1080 Mahjong client. Those
checks remain; the agent cannot click a hidden or differently sized window.
Other transient animation/ambiguous-frame rejections remain possible. No live
agent was launched for this review. Next: user-started validation of the added
Pon layout and Red Five Sou recognition, with ordinary and Yakuman Riichi paths.
