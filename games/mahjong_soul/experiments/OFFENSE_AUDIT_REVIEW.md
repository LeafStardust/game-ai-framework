# Losing-hand audit and simulator action-contract correction

## Actual losing match

Seed 80, candidate seat 2, against call-capable opponents finishes third on 15,000 points with zero wins across four hands. Instrumenting the policy found 41 offensive discard decisions (excluding folds). None sacrifices immediate raw shape Shanten or available improving copies relative to that board's fastest shape options. That does not establish that the choices maximize winning probability: future waits, calls, Yaku bottlenecks and risk can still differ at equal immediate efficiency.

The [call audit](losing_match_call_audit.json) records two accepted Pon and one rejected Pon:

- South Wind Pon keeps the projected legal route at three-Shanten and raises the immediate improving-copy proxy from 21 to 40. South is not this seat's value Wind. The route relies on the retained West Wind pair becoming Yakuhai; it does not yet secure a Yaku.
- West Wind Pon then advances three-Shanten to two-Shanten and secures the seat-Wind Yaku.
- A later 5 Sou Pon using Red Five Sou would move a one-Shanten hand to a two-Shanten legal route, so the policy skips it.

These explain the decisions, not proof of optimal calls or a counterfactual win. In particular, the first opening trades a closed hand for a route with a Yaku bottleneck. A targeted Skip-versus-Pon comparison is needed before changing that decision rule.

## Concrete benchmark bug

RiichiEnv offers physical-copy actions. The adapter exposed each as a separate policy intent, so a hand with two identical normal 5 Sou tiles could receive two identical `discard 5s` actions. The live reader already uses one discard per exact tile label. Riichi offers were duplicated in the same way, and operation entries were repeated per physical action instead of grouped by operation type.

This was redundant scoring work and a contract mismatch. It also lets repeated physical copies occupy a bounded lookahead shortlist. A legal constructed example demonstrates the mechanism: `11 33 55 Pin; 777 Sou; East, South, West, White Dragon, Green Dragon`, with one earlier visible East discard. At two-Shanten, discarding 7 Sou has 14 improving copies and discarding East has 12. Both qualify for the existing two-copy allowance. The former three-entry physical shortlist can be `[7s, 7s, 7s]`, omitting East entirely; the distinct-action shortlist is `[7s, 1z]`. This is a constructed regression example, not an observed missed win in the losing match.

The adapter now exposes one intent per exact label/combination and retains the first engine-legal physical binding. Red and normal fives stay distinct. Riichi remains a declaration followed by the chosen exact discard. Operation offers are grouped by type with unique combinations. No production policy, launcher, native executor or terminal output changed.

## Validation and interpretation

All 797 Mahjong tests passed with the optional simulator enabled. New real-engine regressions cover duplicate normal discards alongside Red Five Sou, first-copy legal binding, unique operation types, and a seeded Riichi offer with two identical 9 Pin copies followed by its actual discard.

[Full-game validation](distinct_action_validation.json) reruns seed 80 seat 2 against both caller and aggressive opponents. Each new replay exactly matches its previous complete MJAI replay, including scores, ranks, wins, deal-ins and starting deal digest. This is adapter parity evidence for those two probes, not a measured win-rate gain or exhaustive equivalence proof. Timing is not compared because cache state and concurrent work differ.

Historical experiment files retain their original source hashes and results. The earlier-hand prototype bounded its shortlist to three entries, which were not guaranteed to be three distinct actions in those simulator runs. Its old results must not be presented as evaluating a guaranteed three-distinct-choice implementation without rerunning it after this correction. That prototype remains disabled; the correction does not imply that lookahead is stronger.

Next: compare the opening South Wind Pon against Skip in the traced hand, using the corrected adapter, then evaluate any proposed call rule on new full-match seeds. No game launch is needed.
