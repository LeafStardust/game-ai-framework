# Balatro Relationships, Motifs, and Composer

This layer sits above Bond Rank and Realization.

```text
Bond Rank      = persistent structural development
Realization    = whether that Bond is functioning now
Relationship   = sparse pairwise synergy/conflict between Bonds
Motif          = known super-additive package with specific components/roles
Composer       = select a coherent combined build from realized/developed Bonds
Build Health   = separate later layer for actual score/survival adequacy
```

## Sparse relationships

Only mechanically meaningful edges are stored. Every unlisted pair is NEUTRAL.

Canonical edges:

```text
CONFLICT
Burnt x No-Discard
Discard x No-Discard
Face Cards x No Face Cards
Vampire x Enhanced Cards

SYNERGY
Burnt <-> Discard
Held Cards <-> Held Retrigger
Held Cards <-> Steel
Held Retrigger <-> Steel
Card Destruction <-> Deck Thinning
```

Relationships must not become an exhaustive pair matrix. Super-additive packages belong to Motifs.

## Motif states

```text
ABSENT    too little of the package exists
POTENTIAL meaningful pieces exist but required components/realization are missing
ACTIVE    the package components exist and the relevant Bonds are realized
MATURE    ACTIVE plus R4+ structural development in all core Bonds
```

## Baron-Mime-Steel

The first canonical motif is intentionally specific:

```text
Baron
Mime
King infrastructure
Steel infrastructure
+
Held Cards
Held Retrigger
Steel
Kings
```

Blackboard cannot substitute for Baron merely because it contributes to Held Cards. This is the purpose of the mechanical-role/component layer: Bond membership describes the strategic axis; the Motif describes the exact synergistic package.

Prescriptions when active include preserving held Kings/Steel, preferring King/Steel creation, valuing hand size, avoiding unnecessary play of engine cards, and strongly valuing Red-Seal Steel/copy effects.

## Composer

The composer considers developed Bonds, removes weaker conflicting Bonds, records sparse synergies, evaluates Motifs, and returns the current coherent composition.

`coherence_score` is a planning priority score only. It may use rank, realization, synergy and motif completion because those describe strategic coherence. It is explicitly **not projected chips or Build Health**.

A coherent composition may still be too weak to clear the next Blind. Score projection and Build Health remain the final power/survival authority.
