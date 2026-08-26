# Balatro D1 Strategy Execution Audit

Status: **Implementation audit complete; current-HEAD local validation pending**

Date: 2026-08-26

This document records the final Red/White D1 execution authorities for mechanics that can be recognized correctly by the build/Bond layer but still played incorrectly if the live action stack ignores their defining behavior. It is a static production audit, not a claim that current HEAD has passed the user's local deterministic suite or live runs.

## Authority hierarchy

D1 remains survival-first:

1. legal action / Boss-Blind constraints;
2. blind-clear probability and feasible clear path;
3. pace/progress and remaining hands/discards;
4. exact current scoring and stateful Joker transitions;
5. survival-equivalent strategy/resource preservation;
6. late deterministic resource/tie behavior.

No execution guard below may turn a losing line into a preferred line merely to preserve a strategy mechanic.

## Stateful Joker transitions propagate through expectimax

`LiveHandDecisionEvaluator.project_play()` returns the scorer's `state_after_scoring`. `LiveBlindClearPlanner` uses that projected state for child search, so persistent Joker mutations are not discarded between hypothetical hands.

This includes stateful mechanics such as Ride the Bus and Green Joker. A face-card Ride-the-Bus reset or a non-face stack increment therefore changes the child state used by the next hypothetical hand rather than only the current hand score.

## No-discard engines

`strategy_execution_guard_policy.py` recognizes the canonical `no_discard` Bond when ACTIVE/MATURE and at least one defining discard-sensitive Joker is present, including Green Joker, Delayed Gratification or Banner.

If baseline D1 chooses DISCARD but a currently visible PLAY already satisfies the D1 pace target, the safe play replaces the convenience discard. If no current play meets pace, survival recovery remains authoritative and the discard is allowed.

The guard therefore prevents a recognized no-discard engine from being ignored without banning strategically necessary discards.

## Burnt Joker first-discard execution

`burnt_bond_execution_policy.py` owns the first-discard activation contract for a developed Burnt Bond.

A Burnt setup discard is allowed to override the generic pace-qualified PLAY preference only when:

- the Burnt development is at least R1 and selected in composition;
- the first discard is still available;
- more than one discard and more than one hand remain;
- the candidate discard preserves at least the configured safe modeled clear probability.

Banner's current-discard chip value may not suppress a safe first Burnt activation: one Banner discard payment is explicitly accepted when it creates permanent Burnt hand-level growth and survival remains safe.

## Hand repetition / Card Sharp

`strategy_execution_guard_policy.py` checks the public current-round hand-play counters for a realized `hand_repetition` engine.

A previously played hand may replace another play or an unnecessary discard only when:

- its modeled clear probability remains within the D1 safe-clear tolerance;
- it meets the current pace target;
- it is already a hand type played this round.

This turns Card Sharp/repetition recognition into actual repeated-hand execution without sacrificing survival.

## Ride the Bus

Ride the Bus' ordinary persistent reset/increment is already carried through non-terminal expectimax via `state_after_scoring`.

A separate terminal edge existed: once a play immediately clears the blind, D1's terminal ranking may prefer additional overkill score even though the next-blind cost of resetting an accumulated Bus stack is outside the current blind horizon.

`ride_the_bus_execution_policy.py` corrects only that dominated terminal case. When the selected guaranteed-clear play scores a face card, it may choose a non-face guaranteed-clear play only if the alternative:

- preserves at least the same expected hands remaining;
- preserves at least the same expected discards remaining;
- preserves at least the same expected generated-consumable count, including Blue Seal rewards;
- sacrifices no additional Gold cards.

The only allowed sacrifice is irrelevant overkill score. Non-terminal, probabilistic-clear, or resource-inferior alternatives remain under ordinary D1 expectimax.

## Purple Seal

`purple_seal_discard_policy.py` does not assign chip-equivalent utility to a Purple Seal. It reserves bounded search-beam coverage for a mechanically distinct discard that can create a Tarot when consumable capacity exists.

Final expectimax still decides whether that branch is worth taking. Survival, progress, hands/discards and score rank before generated-consumable count.

## Steel, Blue Seal and Gold held resources

`held_round_end_resource_policy.py` separates the three mechanics correctly:

- **Steel** is already literal held-card scoring and needs no external preference;
- **Blue Seal** contributes the exact number of generated Planets only on branches that actually clear the round and have consumable capacity;
- **Gold** has no common dollar-to-score conversion inside D1, so Gold-card retention is only a final deterministic tie-break between otherwise equal play candidates.

Pinned held-card strategy preservation remains a separate within-safe-choice signal for held-oriented engines.

## Final installation order

The package installs general strategy execution, target-hand and search guards first, then late Purple-Seal and held-round-end resource authorities, then the Ride-the-Bus terminal guard. The final Red/White competence correction layer does not wrap `StrategyAwareLiveHandActionPolicy.decide`, so it cannot undo these final semantic play choices.

## Hidden-information guarantee

These D1 authorities use only current public hand/deck composition, public round history, modeled Joker state and public Boss-Blind state. They do not use ordered future draw information, RNG state or pseudoseeds.

## Validation status

No tests were run by the assistant. Current-HEAD deterministic and live validation remain the user's local gate. The static execution audit is complete, but any reproduced contradiction on an unchanged validated HEAD should reopen the relevant mechanic rather than be treated as tuning noise.
