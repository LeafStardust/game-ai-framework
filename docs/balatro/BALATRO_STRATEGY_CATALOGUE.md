# Balatro Strategy Catalogue

Canonical catalogue of Balatro strategy tracks (Bonds).

## Status

**Architecture is frozen; catalogue membership is being formulated one Bond at a time.**

The previous strategy-tree nodes and Gold/Silver/Bronze relationships are migration input only. Do not implement the earlier broad candidate list as final truth until each candidate is reviewed and pruned under `BALATRO_STRATEGY_SYSTEM.md`.

## Admission rule

A Bond is a persistent, developable strategic axis. It should normally have meaningful further investment, multiple contributors/persistent state inputs, increasing payoff, and behavior/build consequences at higher development.

A single defining Joker may establish a Bond if it creates a sufficiently deep strategic axis for other components/state to develop.

Do not create Bonds for every Joker, every famous build, every synergy pair, or generic value that does not create a developable plan. Those may instead be contributors, specializations, or composition motifs.

## Bond state vocabulary

```text
LOCKED = a defining prerequisite is absent, so the Bond does not exist yet
R0     = the Bond can emerge naturally, but contribution is below R1
R1-R5  = increasingly developed Bond ranks
```

Not every Bond has a hard unlock prerequisite. Burnt does; Held Cards does not.

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
Burnt Joker absent -> LOCKED
Burnt Joker owned  -> Bond unlocked and contribution determines R1-R5
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

```text
Burnt x No-Discard = CONFLICT
```

Green/Burglar-style zero-discard execution therefore cannot be composed with Burnt. Compatible poker-hand Bonds are selected by the combined-build layer rather than hard-coded into Burnt.

### Implementation

Pure structural evaluator: `games/balatro/bonds/burnt.py`

---

## 2. Held Cards

**Status:** `BOND` — naturally emerging Bond with no hard unlock prerequisite.

**Identity:** build value around cards intentionally retained in hand for held-card payoff, capacity, economy, or later retrigger synergy.

Held Cards is intentionally broader than Baron and intentionally narrower than `everything that happens to remain in hand`. A source contributes only when retaining cards is itself strategically useful.

### Unlock

No defining unlock Joker.

```text
Held Cards always exists as a possible axis
contribution < R1 threshold -> R0
contribution >= threshold   -> R1+
```

This makes Held Cards the reference template for naturally emerging Bonds.

### Provisional thresholds

```text
R1 >= 4
R2 >= 8
R3 >= 13
R4 >= 19
R5 >= 26
```

### Rank authority

**R1 — Emerging**
- recognize held-card payoff;
- stop needlessly spending useful held payoff cards.

**R2 — Established**
- prefer additional held-card infrastructure when compatible;
- preserve useful held cards more consistently.

**R3 — Strong**
- actively shape hand/deck state toward held payoff;
- protect material Held Cards contributors;
- increase the value of Held Retrigger and Steel synergy.

**R4 — Power-engine capable**
- Held Cards may serve as a principal power axis;
- strongly value hand-size and held-payoff efficiency;
- actively seek compatible held-card composition motifs.

**R5 — Capstone**
- aggressively optimize the compatible build around held value;
- very high pivot resistance subject to survival / clearly superior composition.

### Contributor boundary

Current direct/cross-Bond contributors include Baron, Shoot the Moon, Raised Fist, useful Steel/Gold/Blue held infrastructure, extra hand size, and a deliberately modest Mime bridge contribution.

Mime is **not** primarily a Held Cards component: its main role belongs to the separate Held Retrigger Bond. Steel cards similarly contribute here because they are genuine held payoff infrastructure while still belonging strongly to the separate Steel Bond. This is intentional multi-Bond contribution, not duplicate power scoring.

### Relationships / motifs

Held Cards is expected to have sparse synergy edges with at least Held Retrigger and Steel after those Bonds are formulated.

Canonical future motif:

```text
Held Cards + Held Retrigger + Steel + King structure
        -> Baron-Mime-Steel
```

The motif, not Held Cards alone, will encode the super-additive Baron/Mime/Steel-King behavior.

### Realization

The pure evaluator currently reports R1+ as `PARTIAL` until the realization layer can measure whether the agent is actually retaining/triggering valuable held cards. R0 is `DORMANT`.

### Implementation

Pure structural evaluator: `games/balatro/bonds/held_cards.py`

---

## Candidate catalogue status

The broader candidate set remains intentionally unfrozen. Next priority after Held Cards is expected to be Held Retrigger, followed by Steel, so the first multi-Bond composition stack can be represented without inventing a Baron-Mime-Steel Bond.
