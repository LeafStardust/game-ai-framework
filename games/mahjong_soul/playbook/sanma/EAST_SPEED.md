# Three-Player East Speed v0.3

The authenticated three-player East lobby selects this playbook through the existing `--playstyle atk` policy family. It prioritizes speed, then defense, then hand value. South sanma remains unsupported. East games have three scheduled dealer positions but can include repeats and extensions.

## Stronger speed priority

As with Four-Player East Speed, choose the nearest reachable scoring hand, then the most available improving copies, then relative safety, then value. There is zero allowance to sacrifice improving copies for projected Han, and no deliberate Yakuman pursuit. Productive Pon can be considered up to four-Shanten rather than three; same-distance calls must increase improving copies or enable legal Ron. One-Han wins and calls with a valid Yaku are acceptable. Riichi needs one available winning copy rather than two in an unthreatened hand, two rather than four against a single threat, and at least four wall tiles. A Riichi alternative cannot sacrifice available winning copies for value. Offered Ron/Tsumo takes priority over every development action.

Defense still applies to distant hands and multiple threats. Against a single threat, viable close hands can push with six remaining wall tiles and relative danger up to 85, compared with eight and 75 for four-player East. These values are initial heuristics, not calibrated probabilities. The unchanged shared Kan policy rejects Kan under threat and requires no loss of improving copies.

## Sanma rules

All planning loops exclude removed 2 through 8 Man. Chi is unavailable. Man Dora indicators cycle between 1 Man and 9 Man. Seat Winds rotate across three players. North extraction is normalized only when explicitly offered by the server; take the replacement draw when removing North preserves the fastest hand distance, retaining North when it supports a faster shape. Extraction never takes priority over a legal win.

Extracted Norths count as bonus Han, including additional indicator-derived North Dora, and never provide a Yaku. Complete-hand scoring handles the two-opponent Tsumo total and the room's Tsumo-loss versus North-bisection setting. Unknown future indicators or bonuses are not assumed.

## Input validation status

North extraction is wired to the automatic runner using the reviewed 1920x1080 Kita label from session `20261020T052741-339010Z`. Two stable visual checks and a matching server offer are required before one native click. Only a subsequent live own-seat `ActionBaBei` confirms success; duplicate or uncertain delivery remains blocked. Recorded-frame recognition, fake-mouse confirmation and runner preflight are tested. Standard-layout native delivery was subsequently confirmed twice. The combined Kita-plus-Kan layout still needs live confirmation after this fix. No gameplay input was injected during development.

## Validation

Regressions cover routing, speed settings isolation, sanma improving copies, North extraction versus preserving the hand, Dora-only invalidity, North bonus scoring, the Man indicator cycle and both Tsumo payment modes. No three-player live match strength measurement has been performed.

The Kita-plus-Kan layout is also reviewed: Kita shifts to x=730 at 1920x1080. Regression crops come from session `20261020T054957-654100Z`. That session confirmed two standard-layout native North extractions before the combined layout exposed the missing position.
