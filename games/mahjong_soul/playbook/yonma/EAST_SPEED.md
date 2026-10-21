# Four-Player East Speed v0.3

The automatic lobby router selects this playbook for four-player East matches when launched with `MahjongSoulAgent.bat`. The launcher chooses the policy family; the authenticated format chooses East Speed or South ATK. South settings are unchanged. East matches may include dealer repeats and extensions rather than exactly four hands.

Priority is speed, then defense, then attack value. During normal development, minimize reachable scoring-route Shanten, maximize available improving copies, prefer the safer discard when speed is equal, then use projected/scored value to break remaining ties. Expensive routes cannot trade away speed. Deliberate Yakuman pursuit is disabled; any offered legal win is accepted.

Calls may open for one Han, but must preserve a reachable legal Yaku and accelerate the hand. A same-Shanten call needs more available improving copies or must enable legal Ron; calls cannot move backwards or rely on a slower expensive route. Dora alone is never a Yaku. Kan requires at least sixteen wall tiles, no lost improving copies, and no active opponent threat.

Defense can override development when the hand is too distant or a push fails the configured threat checks. One-threat pushes are limited to one-Shanten or Tenpai with viable Yaku, wall and relative danger checks. Multiple threats can trigger a fold. Visible danger rankings are heuristics, not opponent tile knowledge or calibrated deal-in probabilities. This defensive override is specific to East; South remains always-push.

Riichi normally needs two winning copies and at least eight wall tiles. Against one threat it needs four copies; it is not declared into multiple threats. A valuable legal Dama can be retained when Riichi adds less than 25 percent known value. No future Ura or Ippatsu is assumed. Detailed decisions go to recordings; normal terminal output remains the action only.

This is a first heuristic East policy, not a measured win-rate improvement or a full expected-value/placement model.


Speed-first calls may lose projected Han when they preserve legal winning distance and strictly increase available improving copies. The Attack policy value-gain gate does not apply to East Speed. Calls that add no speed, have no reachable Yaku or require an unsafe push remain rejected.

## Ready-hand Yaku proof

A ready open hand can earn its Yaku when the winning tile completes a Dragon or value-Wind triplet. Exact legal Ron scoring now proves that route for the push check even if the partial hand has no completed Yaku yet. This does not relax danger, remaining-wall, available-wait, Furiten or minimum-point limits. South Attack is unchanged.
