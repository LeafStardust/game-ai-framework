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

## Safe-pace wrapper authority

The original `safe_pace_optimization_policy.py` establishes the Red/White action-class doctrine, but `safe_pace_scope_correction.py` restores the public/base `LiveHandActionPolicy` contract and reapplies that doctrine specifically to the production `StrategyAwareLiveHandActionPolicy`. The scoped wrapper is therefore the authoritative live path.

Safe pace still means: a current hand that meets required pace is preferred over speculative multi-step engineering, and when no play reaches pace while a discard remains the agent recovers by discarding instead of burning an under-pace hand.

That wrapper may choose the action class, but it may not replace D1's survival ordering *inside* the class. Current production behavior is therefore:

- deterministic current-hand clears use canonical D1 safe-clear/resource ordering rather than highest overkill score;
- pace-qualified plays are ranked with D1 `_pace_play_key`, whose first authority is full-blind clear probability;
- recovery discards are ranked by the full D1 plan tuple before the local discard heuristic;
- when no discard remains, the forced under-pace play is chosen by full D1 plan quality rather than immediate score alone.

This prevents the production safety wrapper from undoing the full-blind survival estimates already computed by D1 merely because another candidate has a larger current-hand number. The base-layer safe-pace implementation follows the same ordering, but production authority resides in the scoped strategy-aware wrapper.

## Stateful Joker transitions propagate through expectimax

`LiveHandDecisionEvaluator.project_play()` returns the scorer's `state_after_scoring`. `LiveBlindClearPlanner` uses that projected state for child search, so persistent Joker mutations are not discarded between hypothetical hands.

This includes stateful mechanics such as Ride the Bus and Green Joker. A face-card Ride-the-Bus reset or a non-face stack increment therefore changes the child state used by the next hypothetical hand rather than only the current hand score.

## Live hand-rule authority

All late D1 semantic guards that classify a poker hand must use the same state-aware hand rules as canonical D1. Default poker-hand classification is not authoritative when owned mechanics modify hand construction.

Current Red/White corrections apply this consistently to:

- target-hand engines such as Runner and To Do List;
- Card Sharp / hand-repetition execution;
- Burnt Joker discard-hand targeting;
- The Eye and The Mouth Boss-Blind constraints;
- bounded D1 cheap play prefiltering and compact-hand reserve selection.

This prevents Four Fingers, Shortcut or other live rule modifiers from creating disagreements where a late guard calls a hand one type while the exact scorer calls it another, or where a valid modified hand is pruned before expectimax sees it.

## No-discard engines

`strategy_execution_guard_policy.py` recognizes direct discard-sensitive mechanics such as Green Joker and Delayed Gratification immediately, while Banner becomes an execution constraint when the canonical `no_discard` Bond is realized.

If baseline D1 chooses DISCARD, a currently visible PLAY may replace it only when both conditions hold:

- the play satisfies the current D1 pace target; and
- its modeled full-blind clear probability remains within D1's configured safe-clear tolerance of the selected line.

If no such play exists, survival recovery remains authoritative and the discard is allowed.

The guard therefore prevents a recognized no-discard engine from being ignored without preserving Joker value at the cost of materially worse blind survival.

## Castle discard execution

`castle_discard_policy.py` may improve an already-required discard by including cards of Castle's current public suit, but it does not create a discard on its own.

Castle previously carried a separate hard-coded clear-probability allowance. That duplicated survival policy has been removed: an alternative Castle discard must now remain within canonical D1 `safe_clear_probability_tolerance` of the selected line. Its existing retained-score/exactness checks remain secondary shaping rules.

## Burnt Joker first-discard execution

`burnt_bond_execution_policy.py` owns the first-discard activation contract for a developed Burnt Bond.

A Burnt setup discard is allowed to override the generic pace-qualified PLAY preference only when:

- the Burnt development is at least R1 and selected in composition;
- the first discard is still available;
- more than one discard and more than one hand remain;
- the candidate discard remains within canonical D1 `safe_clear_probability_tolerance` of the baseline selected line.

The former Burnt-specific `0.70` absolute floor / `0.08` clear-probability sacrifice is no longer a competing survival policy. D1 owns the survival-equivalence boundary.

Burnt target-hand classification also uses `hand_rules_for_state(state)`, so Four Fingers/other live hand modifiers cannot make the Burnt execution layer disagree with canonical hand classification.

Banner's current-discard chip value may not suppress a survival-equivalent first Burnt activation: one Banner discard payment is accepted when it creates permanent Burnt hand-level growth and the D1 survival boundary is preserved.

## Hand repetition / Card Sharp

`strategy_execution_guard_policy.py` checks the public current-round hand-play counters for a realized `hand_repetition` engine.

A previously played hand may replace another play or an unnecessary discard only when:

- its modeled clear probability remains within the D1 safe-clear tolerance;
- it meets the current pace target;
- it is already a hand type played this round under the current state-aware hand rules.

This turns Card Sharp/repetition recognition into actual repeated-hand execution without sacrificing survival.

## Target-hand engines

`target_hand_engine_policy.py` makes mechanically explicit hand targets affect actual D1 execution. Runner and stateful To Do List targets can win survival-equivalent, pace-qualified tie-breaks rather than existing only in build diagnostics.

Target-hand classification uses `hand_rules_for_state(state)`, so modified hand construction remains identical to canonical D1.

## Pinned strategy safe-pace execution

`pinned_strategy_safe_pace_policy.py` allows the pinned strategy to break close PACE_PLAY ties only inside two existing safety boundaries:

- the candidate remains inside the narrow score-equivalence band used by the policy; and
- its full-blind clear probability remains within D1's configured safe-clear tolerance of the baseline selected line.

The score band alone is not considered a survival guarantee. A held-card or strategy-fit preference cannot replace a materially safer D1 play merely because its immediate score is within 98% of the best pace-qualified score.

## Sixth Sense

`sixth_sense_policy.py` treats first-hand single-6 play as a setup/resource action, not an unconditional mechanic trigger.

When a consumable slot is available, a Sixth Sense harvest may replace the baseline play only when the candidate:

- satisfies the existing pace requirement; and
- remains within D1's configured clear-probability tolerance of the selected line.

When consumable slots are full, preserving the 6 by switching to another play is subject to the same survival-equivalence gate. A 6 is not preserved merely by choosing a weaker line that still meets immediate pace.

## DNA

`aces_dna_hand_policy.py` derives duplication targets from the strongest mechanically linked Bond/composition rather than a static combo table. The existing absolute DNA safety floor remains, but it is not sufficient on its own.

A first-hand DNA setup may replace baseline D1 only when it also remains within D1's configured clear-probability tolerance of the selected line. This applies to both:

- generic Bond-derived rank targets; and
- the Scholar/Ace development path.

Therefore a nominally "safe" 90% DNA setup cannot replace a materially safer baseline clear simply because it crossed the fixed setup floor.

## Boss hand constraints

`boss_hand_constraint_policy.py` keeps The Eye and The Mouth constraints aligned with live hand rules.

For The Mouth, forced-hand redraw shaping may prefer a broader redraw only among candidates that preserve the selected D1 line's clear probability within the configured tolerance. Retained forced-hand structure and redraw width are tie/shape signals beneath survival, not independent authority to replace a safer discard.

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

## Late hand-order authority

`hand_order_policy.py` may reorder a selected play for first-card-sensitive mechanics such as Hanging Chad or Photograph, but the live/debuffed-first signal is subordinate to the exact D1 projection tuple. A reorder cannot prefer a lower-clear-probability line merely because the first selected card is non-debuffed.

## Luchador and Verdant Leaf

Boss-disable Joker sales are also subordinate to modeled survival:

- proactive Luchador use against card-debuff bosses requires an observed debuff and a strict improvement in canonical D1 clear probability;
- Verdant Leaf does not force a Joker sacrifice when the debuffed-card line already clears just as reliably; a sale is chosen only when disabling the blind strictly improves clear probability, with lower Joker loss used to choose among equal survival outcomes.

This preserves one-use or permanent Joker value when the current blind can already be beaten through the active boss effect.

## Final installation order

The package installs general strategy execution, target-hand and search guards first, then late Purple-Seal and held-round-end resource authorities, then the Ride-the-Bus terminal guard. The final Red/White competence correction layer does not wrap `StrategyAwareLiveHandActionPolicy.decide`, so it cannot undo these final semantic play choices.

## Hidden-information guarantee

These D1 authorities use only current public hand/deck composition, public round history, modeled Joker state and public Boss-Blind state. They do not use ordered future draw information, RNG state or pseudoseeds.

## Validation status

No tests were run by the assistant. Current-HEAD deterministic and live validation remain the user's local gate. The static execution audit is complete, but any reproduced contradiction on an unchanged validated HEAD should reopen the relevant mechanic rather than be treated as tuning noise.
