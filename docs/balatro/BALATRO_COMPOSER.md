# Balatro Relationships, Motifs, and Composer

The composer sits above Bond Rank and Realization and below Build Health / score projection.

```text
Bonds + Realization
  -> sparse relationships
  -> motifs
  -> combined composition
  -> Build Health / score projection
```

## Sparse relationships
Only genuine Bond-level SYNERGY/CONFLICT edges are stored. All other pairs are NEUTRAL. Relationship bonuses must be counted once per unique pair.

## Motifs
Motifs represent super-additive packages whose behavior cannot be captured safely by additive Bond development alone.

Current canonical motifs:

```text
baron_mime_steel
photograph_hanging_chad
vampire_midas
burnt_target_level
low_rank_hack_retrigger
```

Motif states:

```text
ABSENT    insufficient package identity
POTENTIAL recognizable package but one or more material pieces/realization gates missing
ACTIVE    package complete and relevant Bonds realized
MATURE    ACTIVE plus high structural development where applicable
```

`missing_count` is the composer-facing motif distance. It is deliberately simple and should not be mistaken for acquisition probability or economic cost.

## Composer
The composer selects a coherent set of developed Bonds, resolves explicit conflicts, records unique synergies, evaluates motifs, and emits prescriptions from ACTIVE/MATURE motifs.

`coherence_score` is not projected score power. It rewards structurally developed, realized, mutually compatible plans and motif completion.

## Pivot resistance
High-rank Bonds create abandonment cost:

```text
R1 low
R2 modest
R3 meaningful
R4 strong
R5 very strong
```

Pivot resistance is never a lock. A clearly superior or survival-required plan may still replace a mature composition.

## No double counting
The composer must not:

- count the same relationship edge more than once;
- convert Bond overlap into imaginary score;
- treat motif bonuses as direct chip/mult estimates;
- count a Joker twice merely because it contributes to several compatible Bonds.

The following stage, Build Health / score projection, determines whether the coherent plan actually clears current and future blinds.
