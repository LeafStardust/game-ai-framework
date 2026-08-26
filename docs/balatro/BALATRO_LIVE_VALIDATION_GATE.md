# Balatro Live Validation Gate

Date: 2026-08-27

This gate starts after deterministic Red/White validation completed locally with:

```text
2647 passed, 1 skipped
```

The sole skip came from an empty parametrization over `BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS`. That set is currently empty and the same test module already proves exhaustive/disjoint Tarot classification, so the zero-case parametrized test provided no current coverage. Commit `2881bfe` removes it rather than carrying a permanent meaningless skip.

The user subsequently reported the full deterministic suite green after the Celestial regression fixes and the updated Celestial probability contract.

No tests or live games were run by the assistant.

## Live blocker 1 — first SHOP decision does not complete

Observed production attempt:

- session: `balatro-20260826T170420Z-1cee5969`
- attempt: `balatro-20260826T170420Z-1cee5969-attempt-001`
- Red Deck / White Stake
- Ante 1 / Round 1
- SHOP after the first blind
- money: $9
- owned Jokers: 0 / 5

The uploaded JSONL reaches a successful `END_ROUND` transition into a fully settled SHOP and then contains no SHOP `decision` event. The supervisor remains `THINKING`, so the blocker occurs during policy computation before bridge execution.

Observed visible shop state included:

- Zany Joker, $4
- 8 Ball, $5
- Buffoon Pack, $4
- Celestial Pack, $4
- Hieroglyph, $10
- authoritative public eligible Joker generation pools
- authoritative public Tarot/Spectral generation pools

This rules out a missing settled checkpoint or a failed shop click as the initial cause.

### Root cause

The final Celestial D8 wrapper in `planet_pack_fallback_policy.py` evaluated `_celestial_expected_selection_utility()` before its authoritative hand-development headroom/reserve veto.

For the observed first shop:

- there is no pinned hand goal;
- no hand has the minimum three observed plays required by `_observed_hand_goals()`;
- there is no Planet-use scaler;
- therefore `_celestial_headroom(state) == 0` and the pack must be `HOLD` regardless of its finite Planet expectation.

Nevertheless the old order first enumerated the public eligible Planet pool and repeatedly deep-copied/scored literal before/after states. That work could not alter the eventual HOLD and was large enough to block interactive shop progression.

### Repair

- commit `3cc694d` adds `celestial_shop_headroom_fast_path.py`;
- commit `068c946` installs that fast path from the final Red/White correction layer, after existing D8/Celestial wrappers;
- Celestial states that already fail the exact existing headroom or reserve condition return `HOLD` immediately;
- states that can still buy delegate unchanged to the full finite public-Planet expectation;
- no threshold, utility, hidden-state assumption, RNG access, or acquisition semantics were changed.

### Deterministic regression from the first fast path

The first fast-path implementation returned a synthetic zero-valued `ShopBoosterRecommendation` when the headroom/reserve veto fired. That preserved the final `HOLD` action but incorrectly bypassed observable D8 accounting:

- `price_penalty`, `interest_penalty`, and `reserve_penalty` became zero;
- the parent shared `RunResourceValuator` was not invoked;
- voucher interest-cap mechanics such as Seed Money therefore disappeared from the recommendation;
- pressured Celestial fixtures lost the expected higher reserve penalty.

User validation exposed three failures covering exactly those contracts.

Repair:

- commit `6315038` keeps the shortcut but reproduces the ordinary cheap parent D8 Celestial calculation before returning the forced HOLD;
- public layout metadata, build need, generic option utility, and the exact shared money/interest/reserve valuation are preserved;
- only the later finite Planet expectation is skipped when it cannot alter the final HOLD;
- states with adequate headroom and reserve still delegate unchanged to the complete exact Celestial policy;
- commit `b0dc146` updates one stale test that compared the generic parent family prior against the exact specialized Planet-pool probability, which are different semantic quantities.

The user then reported the deterministic suite green.

## Live blocker 2 — Buffoon public-Joker expectation blocks SHOP

Observed production attempt:

- session/run prefix: `balatro-20260826T173550Z-1fb6296a`
- attempt: `balatro-20260826T173550Z-1fb6296a-attempt-001`
- Red Deck / White Stake
- Ante 1 first SHOP
- money: $9
- owned Jokers: 0 / 5
- visible boosters include Buffoon Pack and Mega Celestial Pack

The new uploaded JSONL again reaches a successful transition into a settled SHOP and then emits no SHOP `decision` event. Mega Celestial is already cheap to reject through the repaired reserve/headroom fast path, so the remaining expensive branch is Buffoon.

The authoritative live Joker generation catalogue in this checkpoint contains:

- Common: 57 eligible records
- Uncommon: 49 eligible records
- Rare: 10 eligible records
- total: 116 eligible public Joker records
- public edition rate: 1.0

### Root cause

`buffoon_booster_expectation_policy.py` delegates unopened Buffoon value to `RerollJokerExpectationEvaluator`. The old evaluator walked every eligible public Joker, every public initial-state expansion, and every edition branch, and sent each branch through the fully wrapped Red/White `PlaybookJokerAcquisitionPolicy` plus D14 normalization.

For a 116-record live catalogue this creates hundreds of full D2/whole-build evaluations for one unopened $4 pack before D14 can emit any SHOP action. The model is public-information-correct but not runtime-bounded, so it can stall the interactive supervisor.

The same evaluator is also shared by D11 future-Joker reroll value, making this a common public-Joker expectation runtime defect rather than a Buffoon-only bridge issue.

### Repair

Commit `3c9c70d` bounds `RerollJokerExpectationEvaluator` without introducing hidden-information assumptions or a synthetic optimistic family prior:

- pools with at most 24 public records retain the previous exact full D2/D14 integration, preserving deterministic fixture behavior;
- larger pools are preflighted in full so unresolved or unmodeled eligible records still fail closed;
- expensive D2 scoring uses a deterministic rarity-stratified subset, never a named Joker tier list;
- at most three public records per rarity are selected for expensive valuation in the large-pool path;
- a hard cap of 48 fully wrapped D2 calls prevents initial-state/edition expansion from becoming unbounded;
- every unevaluated record or edition branch retains its real probability mass but contributes zero;
- omitted mass is never renormalized over the evaluated subset, so the result is a conservative lower bound rather than fabricated future value;
- D2/D14 remains authoritative for every branch that contributes positive value;
- exact future identity, edition, RNG state, pseudoseed, pool order, and hidden price remain unobserved.

This lower-bound treatment can understate Buffoon/reroll value, but it cannot overstate unseen future value and it guarantees a finite public-Joker evaluation budget at the SHOP boundary.

## Live blocker 3 candidate — exact Standard-pack contextual fan-out

Observed production attempt:

- session: `balatro-20260826T175657Z-ed49c8ab`
- attempt: `balatro-20260826T175657Z-ed49c8ab-attempt-001`
- Red Deck / White Stake
- Juggler was bought successfully in the preceding SHOP;
- the agent then ended that shop, cleared the next blind, cashed out, and reached the following settled SHOP;
- money: $11
- owned Jokers: Juggler
- visible offers: Hack $6, Baron $8, Arcana Pack $4, Standard Pack $4, Clearance Sale $10.

The user described this as stopping after buying a Joker, but the JSONL shows the Juggler transaction and subsequent round completed. The actual stall begins only after the next SHOP is settled and before its first SHOP decision event.

D11 is not the dominant path in this state: the normal $5 reroll would leave $6 and is rejected by the $10 post-reroll reserve before future-offer EV. Clearance Sale is also cheap because its parent value is policy-contingent and therefore fails closed at zero rather than projecting hypothetical purchases.

The dominant remaining identified hot path is unopened Standard-pack D8 value. `StandardBoosterExpectationEvaluator` integrates the exact public generator over 13 ranks × 4 suits × 9 enhancement states × 4 edition states × 5 seal states = 9,360 branches. Before the repair, each branch called the contextual B6 playing-card build evaluator even though the same build profile was already cached.

### Repair

Commit `ace91f6` preserves the exact Standard generator, branch probabilities, direct D9 values, vanilla dilution, deck-growth value, and per-branch `max(0, score)` clipping, but factorizes the contextual B6 term:

- rank context is evaluated once for each of 13 ranks;
- suit context once for each of 4 suits;
- enhancement context once for each of 8 non-null enhancements;
- edition context once for each of 3 non-null editions;
- seal context once for each of 4 non-null seals;
- all 8 × 4 enhancement/seal pairs are evaluated once to preserve the only current cross-axis overlap (`held:effect`, shared by Steel/Gold and Blue Seal) through an explicit non-additive correction;
- the 9,360 exact probability branches are still integrated unchanged;
- contextual graph calls are therefore reduced from 9,360 to exactly 64 without changing Standard-pack EV semantics.

Commit `6bae6d8` adds a regression asserting the real unopened Standard evaluator remains bounded at exactly 64 contextual B6 calls.

This is currently a **live blocker candidate**, not yet claimed as the proven sole cause of the third stall; the next user deterministic run and live attempt will determine whether Arcana or another remaining path also needs a runtime bound.

Validation status: **pending user local deterministic rerun on current HEAD, then a fresh three-attempt Red/White live baseline**.

## Current commands

Deterministic suite:

```powershell
python -m pytest tests/balatro -q
```

Three-attempt Red/White production baseline:

```powershell
.\BalatroAgentToggle.bat --three
```

## Gate rule

Do not begin numerical calibration/Optuna until the deterministic suite remains green on the live-response repairs and the fresh three-attempt baseline completes SHOP decisions without semantic/runtime stalls.
