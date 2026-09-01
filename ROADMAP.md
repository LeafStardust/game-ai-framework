# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest command must use `-q`.
- Preserve exact Balatro mechanics, public-state legality, boss rules, affordability, and hidden-information boundaries.
- Prefer canonical ownership over late wrappers/rescue layers.
- Bond/composition and Build Health are evidence/planning layers, not direct score/action authorities.
- Numerical tuning must not compensate for missing strategy semantics.
- Before Bond/strategy work, read `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`.
- Use scoped Conventional Commit messages.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

The immediate project goal is not merely to detect Bonds. It is to make the production agent **use them Currency-Wars-style as a persistent run-level strategy system**.

# Source architecture — Currency Wars is the controlling mental model

The Bond system is explicitly derived from **Honkai: Star Rail Currency Wars**.

Canonical mapping:

```text
Currency Wars character        = Balatro Joker/card/persistent state
Currency Wars Bond             = Balatro strategic axis
Bond quota/rank                = weighted contribution + R0-R5 development
Currency Wars player strategy  = Balatro candidate/pinned composition
```

The intended behavior is:

```text
RNG supplies components
→ components contribute to one or more Bonds
→ Bonds develop independently
→ compatible Bonds/mechanics compose into a coherent strategy
→ the strategy becomes more committed as evidence strengthens
→ the agent deliberately develops, preserves, and exploits that strategy
→ the agent pivots only when survival/economy or a materially better strategy justifies it
```

**A Bond system that only detects a strategy and adds local tie-break bonuses is incomplete.**

Currency-Wars-style implementation requires a coherent strategy to shape the run across all relevant decision owners while remaining subordinate to legality, survival, affordability, boss correctness, and justified pivots.

# Canonical causal chain

```text
public game state
→ literal Balatro mechanics
→ Bond evidence + semantic mechanics
→ Bond development / realization
→ coherent candidate strategy / commitment
→ persistent current strategy plan
→ construction goals + preservation + execution preferences
→ canonical D1/D2/D3/D4/D9/D11/D14 owners consume the SAME strategy intent
→ final legal/survival-aware actions
→ persistent build development
→ scoring payoff / run outcome
```

The current implementation is strongest through **candidate strategy / commitment**. The major unresolved gap is the next section: **persistent strategy execution across the agent**.

# Strategy authority contract

Development, realization, and commitment remain separate:

```text
Development = Bond R0-R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Commitment  = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

## FORMING = construction authority

FORMING may:
- expose a bounded strategy plan;
- emit `seek_feature:*`, `seek_component:*`, `seek_bond:*`, or equivalent construction goals;
- influence admitted acquisition/development choices;
- establish a run-level direction that relevant construction consumers should understand.

FORMING may not merely by existing:
- protect components from replacement;
- dictate hand execution;
- impose held-card preservation;
- create unjustified pivot resistance;
- be internally promoted to PINNED.

## PINNED+ = preservation/execution authority

PINNED / ESTABLISHED / DOMINANT may additionally influence preservation/execution and stronger pivot resistance, while remaining subordinate to:
- legality;
- deterministic or materially safer survival;
- affordability/economy;
- boss correctness;
- materially stronger projected alternatives.

# Current implementation state — IMPORTANT

## Baseline gameplay

Baseline gameplay has already undergone substantial competence work. Do **not** restart a generic baseline-tuning phase.

The agent can play legal Balatro, project scoring/Jokers, handle boss constraints, search D1 survival lines, make shop decisions, and manage basic resources. Live validation exposed and retained two genuine D1 fixes:

- `7cbc13439c7ec0f047772dc01eb4b4626feeb47d` — preserve the deepest successfully completed Joker-aware D1 search when a later search times out.
- `7ddf49542e652d9b2583568b693b0761a5e28097` — `discard_width=1` now means best discard candidate overall rather than structurally forcing a one-card discard.

These fixes remain valid. They do **not** change the active project target back to baseline competence.

Only fix another baseline defect if it is discovered concretely while completing strategy execution. Do not launch another broad baseline audit.

## Bond representation / composition

The redesigned Bond layer can already:
- derive weighted Bond contributions from public mechanics;
- calculate R0-R5 development;
- represent realization separately;
- infer semantic links;
- form candidate strategies;
- assign commitment states;
- expose motifs, goals, missing features/components, prescriptions, and diagnostics.

This is meaningful infrastructure, but it is **not sufficient** by itself.

## Strategy execution — CURRENT PRIMARY GAP

The production agent currently has several **local strategy-aware policies**, but no fully proven Currency-Wars-style run-level execution path.

Examples of what currently exists:
- D1 recomputes Bond composition and uses strategy/Bond fit inside canonical survival arbitration.
- Burnt has explicit first-discard development evidence.
- Held-card/Steel has PINNED+ held-card preservation behavior.
- D2 Joker acquisition can reward Bond/strategy transitions and filling strategy-plan gaps.

But this has not proven that:

```text
"I am building strategy X"
→ all relevant later shop/pack/deck/card/hand decisions understand X
→ they deliberately reinforce X when appropriate
→ X persists as the current run direction across rounds
→ X is exploited for actual payoff
→ X is abandoned only through a justified pivot
```

A particularly important warning from current D1 code: `StrategyAwareLiveHandActionPolicy` accepts `strategy_tracker` but discards it (`del strategy_tracker`) and recomputes composition from current state. Recalculation from public state is valid evidence, but the architecture must still provide coherent run-level strategy intent to every relevant consumer. Do not mistake recomputation plus local bonuses for a complete strategy controller.

# Three pilot strategies — NOT FULLY VALIDATED YET

The three pilots are the controlled subset for proving the Currency-Wars-style execution architecture. They are **not finished merely because controlled local tests are green**.

## Pilot A — Burnt / persistent hand-level development

Already proven locally:
- real `BurntJoker` hard-unlocks Burnt;
- `burnt_target_level` can form naturally;
- D1 can prefer the target first discard among safe alternatives;
- the persistent hand-level mechanic is real;
- survival overrides development greed.

Still must prove/implement as one coherent strategy:

```text
Burnt acquired
→ Burnt strategic axis develops
→ target hand is selected coherently
→ strategy persists across rounds
→ first-discard leveling repeatedly develops that target when safe
→ relevant shop/pack/Planet/support decisions reinforce the target-hand plan
→ later D1 deliberately exploits the developed hand
→ strategy may pivot only for a justified stronger/survival line
```

Do not call Burnt complete until every relevant arrow has a canonical consumer and an end-to-end production proof.

## Pilot B — Deck shaping / deck thinning

Already proven locally:
- Erosion can form a deck-thinning direction;
- Trading Card can deepen it;
- D2 can value reinforcement for the correct strategy reason;
- same-purchase self-synergy inflation was fixed.

Still must prove/implement:

```text
thinning/destruction evidence appears
→ coherent strategy direction forms
→ acquisition consumers seek compatible thinning/destruction support
→ actual deck-removal/transform consumers receive the same strategy intent
→ removal targets are strategy-correct
→ persistent deck composition improves toward the plan
→ later decisions exploit the improved deck
→ pivots remain justified rather than accidental
```

## Pilot C — Held-card / Steel

Already proven locally:
- Baron alone can form the intended direction;
- Baron + Mime can naturally reach PINNED+;
- D1 can preserve a relevant held King among safe-equivalent actions;
- survival can force the engine card to be spent.

Still must prove/implement:

```text
held-card payoff infrastructure appears
→ FORMING construction plan emerges
→ shop/pack/deck consumers seek Kings/Steel/retrigger/hand-size support as appropriate
→ strategy naturally reaches PINNED+
→ relevant cards/components gain preservation authority
→ D1 exploits held scoring/retrigger mechanics
→ engine development continues coherently across rounds
→ materially stronger/survival pivots still work
```

# What the 30 live attempts actually proved

Three 10-attempt Red/White batches produced 0/30 wins.

Do **not** interpret that as a valid test of all three pilot Bonds:
- Burnt and Deck-Thinning opportunities were sparse in the random samples;
- the batches did expose two real D1 defects, now fixed;
- they did not establish that the three pilot strategies are fully built and followed end-to-end;
- therefore they do not settle Bond-system usefulness.

Do not request another random 10-run batch at this stage.

# ACTIVE PHASE — CURRENCY-WARS-STYLE STRATEGY EXECUTION

This is the only active architectural task unless a concrete incidental bug blocks it.

## Goal

Turn the existing Bond/composer output into a coherent **run-level strategy contract** consumed by every relevant canonical owner.

This does **not** mean adding a giant central policy that directly chooses every action. Preserve canonical ownership.

Instead:

```text
Bond/composer
→ produces one authoritative current strategy state/plan
→ canonical decision owners query/receive that plan
→ each owner translates relevant goals/prescriptions into bounded domain-specific preferences
→ survival/economy/legality remain authoritative locally
→ strategy state updates after public state changes
→ pivot logic decides when the current strategy should be replaced
```

## Required implementation properties

### 1. Authoritative strategy state

There must be one coherent representation of the current strategy direction containing at least:
- strategy ID / identity;
- commitment;
- contributing Bonds/components;
- target hand/features where applicable;
- current goals / missing features / missing components;
- prescriptions;
- completion/strength/confidence;
- reasons for retaining or pivoting.

It may be recomputed from public state rather than stored as hidden mutable memory, but **all consumers must resolve the same strategy**, and continuity/pivot semantics must be explicit rather than accidental.

### 2. Consumer coverage

For each pilot, enumerate every decision owner needed to build and use it. For each owner classify:

```text
REQUIRED + WIRED + PROVEN
REQUIRED + WIRED + UNPROVEN
REQUIRED + NOT WIRED
NOT RELEVANT
```

At minimum audit the existing D1/D2/D3/D4/D9/D11/D14 owners and any pack/consumable/deck-shaping owners actually required by the pilot.

Do not add strategy hooks to irrelevant consumers just for completeness.

### 3. Construction semantics

FORMING strategies must actively guide construction through admitted choices:
- seek missing compatible components/features;
- deepen existing relevant Bonds;
- prefer multi-Bond/slot-efficient pieces where mechanically justified;
- avoid unrelated Bond collection;
- remain subordinate to immediate survival/economy.

### 4. Preservation/execution semantics

Only PINNED+ obtains stronger preservation/execution authority.

That authority must be strategy-specific and mechanically grounded, not a generic numeric bonus.

### 5. Pivot semantics

The run must not accidentally forget a coherent strategy because a single state recomputation slightly changes rankings.

Likewise it must not cling to a bad strategy forever.

Pivot evaluation must compare:
- current realized engine;
- current strategy commitment/development;
- candidate alternative coherence/strength;
- missing-piece distance;
- money/slots/runway;
- abandonment cost;
- survival risk;
- materially stronger projected alternatives.

### 6. End-to-end deterministic proofs before live validation

Before asking the user for another live run, each pilot must have a multi-decision production-path proof showing strategy continuity across the decisions it actually needs.

The proof must use real public modeled state and real production policies. Do not inject a fake strategy candidate into the consumer merely to make the test pass.

# EXACT NEXT ACTION

1. **Do not perform another baseline competence audit.**
2. **Do not run another random 10-attempt live batch.**
3. **Do not begin the remaining ~43-Bond refurbishment yet.**
4. Treat the three pilot Bonds as locally functional but **not end-to-end complete**.
5. Audit the strategy-to-consumer wiring for Burnt first, because it is the cleanest persistent-development vertical.
6. Produce a Burnt consumer map covering every decision needed for:
   - target-hand selection;
   - repeated first-discard development;
   - compatible acquisition/Planet/support construction;
   - later target-hand exploitation;
   - survival override;
   - justified pivot.
7. For every missing Burnt consumer path, implement the behavior in the existing canonical owner rather than through a late wrapper.
8. Add a multi-round/multi-decision production regression proving the full Burnt chain with no injected strategy candidate.
9. Repeat the same consumer-map → wire → production-proof process for Deck Thinning and Held-card/Steel.
10. Only when all three pilots have coherent end-to-end strategy execution should they become the template for systematically refurbishing the remaining ~43 Bonds.
11. Only after that should live validation resume, preferably targeted to observe completed pilot strategies rather than another blind arbitrary batch.

# Definition of progress

Every work cycle in this phase must end in one of two concrete states:

```text
A required strategy-consumer link is proven correct
OR
A missing/incorrect strategy-consumer link is identified and repaired
```

Do not use open-ended live runs as the primary discovery mechanism.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence — COMPLETE
5. Phase 4 — resource semantics — COMPLETE
6. Phase 5 — initial live validation — COMPLETE
7. Phase 6A — strategy authority contract — COMPLETE / GREEN
8. Phase 6B — three-pilot local deterministic proofs — COMPLETE / GREEN
9. Phase 6C — limited local production integration — COMPLETE / GREEN BUT INSUFFICIENT
10. Phase 6D — random controlled live pilot attempts — COMPLETE; 0/30, exposed D1 defects but did not fully validate pilots
11. **Phase 6E — Currency-Wars-style run-level strategy execution for the three pilots — ACTIVE**
12. Phase 6F — three-pilot end-to-end production proofs — BLOCKED ON 6E
13. Phase 6G — targeted live pilot validation — BLOCKED ON 6F
14. Phase 6H — systematic refurbishment of remaining ~43 Bonds using proven architecture — BLOCKED ON 6G
15. Phase 6I — broader tuning / future stake+deck progression — BLOCKED

# Guardrail against repeating the previous loop

Do not repeat this cycle:

```text
Bond incomplete
→ generic baseline detour
→ random live batch
→ another generic audit
→ return to Bond incomplete
```

The active question is now explicit:

> **Can the production agent take a coherent Bond-derived strategy and deliberately build, preserve, execute, and pivot that strategy Currency-Wars-style across the whole run?**

Until the answer is proven YES for the three pilots, stay on this problem.