# Three-Player East Speed v0.1

The authenticated three-player East lobby selects this playbook through the existing `--playstyle atk` policy family. It prioritizes speed, then defense, then hand value. South sanma remains unsupported. East games have three scheduled dealer positions but can include repeats and extensions.

## Stronger speed priority

As with Four-Player East Speed, choose the nearest reachable scoring hand, then the most available improving copies, then relative safety, then value. There is zero allowance to sacrifice improving copies for projected Han, and no deliberate Yakuman pursuit. Productive Pon can be considered up to four-Shanten rather than three; same-distance calls must increase improving copies or enable legal Ron. One-Han wins and calls with a valid Yaku are acceptable. Riichi needs one available winning copy rather than two in an unthreatened hand, two rather than four against a single threat, and at least four wall tiles. A Riichi alternative cannot sacrifice available winning copies for value. Offered Ron/Tsumo takes priority over every development action.

Defense still applies to distant hands and multiple threats. Against a single threat, viable close hands can push with six remaining wall tiles and relative danger up to 85, compared with eight and 75 for four-player East. These values are initial heuristics, not calibrated probabilities. The unchanged shared Kan policy rejects Kan under threat and requires no loss of improving copies.

## Sanma rules

All planning loops exclude removed 2 through 8 Man. Chi is unavailable. Man Dora indicators cycle between 1 Man and 9 Man. Seat Winds rotate across three players. North extraction is normalized only when explicitly offered by the server; take the replacement draw when removing North preserves the fastest hand distance, retaining North when it supports a faster shape. Extraction never takes priority over a legal win.

Extracted Norths count as bonus Han, including additional indicator-derived North Dora, and never provide a Yaku. Complete-hand scoring handles the two-opponent Tsumo total and the room's Tsumo-loss versus North-bisection setting. Unknown future indicators or bonuses are not assumed.

## Input validation status

The policy and readable suggestions support North extraction. The automatic runner recognizes verified three-player AI rooms and can use its existing visually guarded controls. The North-extraction button has no reviewed sample yet: it reports a manual action rather than guessing a click. A complete autonomous three-player match is not validated until that control and the actual three-player UI have been recorded and tested. Do not treat policy tests as native click calibration. Recordings remain available for diagnosing layout problems.

## Validation

Regressions cover routing, speed settings isolation, sanma improving copies, North extraction versus preserving the hand, Dora-only invalidity, North bonus scoring, the Man indicator cycle and both Tsumo payment modes. No three-player live match strength measurement has been performed.
