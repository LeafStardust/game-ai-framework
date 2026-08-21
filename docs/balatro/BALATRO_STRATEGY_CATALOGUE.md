# Balatro Strategy Catalogue

Canonical catalogue of Balatro strategy tracks (Bonds).

## Status

**Architecture is frozen; catalogue membership is being formulated one Bond at a time.**

The previous strategy-tree nodes and Gold/Silver/Bronze relationships are migration input only. Do not implement the earlier broad candidate list as final truth until each candidate is reviewed and pruned under `BALATRO_STRATEGY_SYSTEM.md`.

## Admission rule

A Bond is a persistent, developable strategic axis. It should normally have meaningful further investment, multiple contributors/persistent state inputs, increasing payoff, and behavior/build consequences at higher development.

A single defining Joker may establish a Bond if it creates a sufficiently deep strategic axis for other components/state to develop.

Do not create Bonds for every Joker, every famous build, every synergy pair, or generic value that does not create a developable plan. Those may instead be contributors, specializations, or composition motifs.

## Classification during catalogue audit

For every old node/candidate classify it as one of:

- `BOND` — independently developable track;
- `MINOR_BOND` — useful auxiliary track with limited strategic authority if this category survives pruning;
- `SPECIALIZATION` — meaningful sub-form of another Bond;
- `CONTRIBUTOR` — strengthens one or more Bonds but is not itself a Bond;
- `MOTIF` — known composition of multiple Bonds/components;
- `MERGE` — concept belongs inside another Bond;
- `REMOVE` — not useful as a strategic concept.

## Required definition for every accepted Bond

Every accepted Bond must define:

1. strategic identity;
2. optional hard unlock prerequisite(s);
3. weighted contributors;
4. Bond-specific R1-R5 thresholds;
5. Bond-specific rank effects/prescriptions;
6. realization conditions (`DORMANT/PARTIAL/ACTIVE/MATURE`);
7. explicit sparse `SYNERGY` / `CONFLICT` edges only where meaningful;
8. relevant motif participation;
9. unusual pivot/transition considerations if any.

## Important distinction

Bonds are not named builds.

```text
Held Cards       = Bond
Held Retrigger   = Bond
Steel            = Bond

Baron + Mime + Steel Kings
                  = composition motif / strategy
```

A component can contribute to several Bonds without becoming a Bond itself. Blueprint/Brainstorm/DNA-like components may be strategically crucial bridge contributors while remaining outside the catalogue.

---

# Accepted Bonds

## 1. Burnt

**Status:** `BOND` — first accepted/template Bond.

**Identity:** deliberate permanent specialization of a chosen poker hand through the Burnt-centered first-discard leveling engine.

### Unlock

```text
Burnt Joker absent -> LOCKED / R0
Burnt Joker owned  -> Bond unlocked
```

Burnt Joker is the only hard unlock prerequisite currently accepted. After unlock, there are **no required sequential contributors for R2-R5**. Telescope, Blueprint, Brainstorm, Blue Seal infrastructure, target-hand development, Space Joker and discard capacity are alternative/additive paths into one weighted contribution pool.

### Target hand

Burnt does not choose an intrinsic poker hand.

```text
strongest compatible poker-hand Bond / combined-build plan
        -> Burnt target

no meaningful hand specialization
        -> HIGH_CARD fallback
```

Existing permanent hand investment creates switching resistance so minor score fluctuations do not cause target oscillation.

### Provisional thresholds

```text
R1 >= 8
R2 >= 12
R3 >= 17
R4 >= 23
R5 >= 30
```

These are provisional Red/White values and may be telemetry-calibrated later. They are contribution thresholds, not item gates.

### Rank authority

**R1 — Emerging**
- recognize first-discard permanent level value;
- default to High Card if no stronger compatible poker-hand plan exists.

**R2 — Established**
- reinforce the selected target hand;
- prefer targeted hand-level infrastructure;
- preserve reasonable first-discard access.

**R3 — Strong**
- actively shape resources around the target hand;
- protect material Burnt contributors;
- increase search/acquisition value for Burnt reinforcement.

**R4 — Power-engine capable**
- Burnt may serve as the principal power engine;
- if the blind is already safely/trivially clearable, use the first-discard level-up before scoring rather than wasting permanent scaling;
- strongly prioritize targeted permanent hand scaling.

**R5 — Capstone**
- aggressively optimize the compatible combined build around Burnt;
- very high pivot resistance; abandon only for survival or a clearly superior composition.

### Realization

Rank measures development only. Realization separately measures whether the first-discard engine and target-hand specialization are actually being exploited correctly.

A high-rank Burnt Bond can still be `PARTIAL` if the agent repeatedly fails to use safe first-discard upgrades, and Build Health can still report that a coherent Burnt build is too weak to survive.

### Relationships

Explicit known relationship:

```text
Burnt x No-Discard = CONFLICT
```

Green/Burglar-style zero-discard execution therefore cannot be composed with Burnt. Compatible poker-hand Bonds are selected by the combined-build layer rather than hard-coded into Burnt.

### Implementation

Pure structural evaluator: `games/balatro/bonds/burnt.py`

The evaluator is intentionally isolated from legacy Primary/Secondary/Third runtime selection while the Bond catalogue is still being formulated. It is the reference implementation for subsequent Bonds.

---

## Candidate catalogue status

The broader candidate set remains intentionally unfrozen. The immediate next task after validating Burnt is to select and formulate the next Bond under the same rules rather than bulk-importing the old strategy tree.
