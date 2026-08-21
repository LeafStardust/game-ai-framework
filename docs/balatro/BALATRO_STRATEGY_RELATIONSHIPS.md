# Balatro Strategy Relationships / Contribution Catalogue

> **Architecture migration note (2026-08-21):** this file remains the canonical detailed relationship dataset, but its rows are now interpreted as the seed **contribution matrix** for the Bond-like strategy-track architecture defined in `BALATRO_STRATEGY_TREE_RULES.md`. A Joker may contribute to multiple tracks simultaneously. Tracks are to be developed independently and composed into a compatible combined build; they are not ultimately intended to compete as exactly Primary/Secondary/Third candidate builds. Existing Gold/Silver/Bronze/Banned values remain the effective Red/White runtime contract until the migration is implemented and recalibrated.
>
> **Do not add new relationships merely to manufacture legacy commitment.** Add them when the mechanic genuinely advances that track. Gold/Silver/Bronze are currently coarse contribution strengths; Banned is a true mechanical conflict. Future editors should preserve this dataset while migrating consumers toward track meters, rank thresholds, compatibility/synergy composition, a power-engine selector, and rank-aware prescriptions.
>
> **Authoritative composition corrections:** Burnt and Green conflict; Burnt and Burglar conflict; Green and Burglar synergize. Burglar must not be treated as Burnt support. Developed Burnt must deliberately use safe first-discard upgrades. Developed Ride the Bus/no-face should avoid playing face cards when a safe comparable non-face line exists. Scholar/Aces/DNA should be valued as compatible multi-track reinforcement around Burnt + cheap-hand compositions rather than as rival global strategies.

Development reference for [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md).

## Runtime implementation status

- **Current runtime:** legacy strategy tracker plus state-aware conditional relationships, Build Health, realized-engine analysis, shop/D1 prescriptions and tree migration layers.
- **Target runtime:** all strategy tracks evaluated simultaneously; compatible tracks composed into one build; one power engine selected; prescriptions merged from the combined build.
- Sections below record the effective relationship contract and remain useful migration data. Conditional text is part of that contract.

## Evidence weights — current Red / White runtime calibration

| Evidence | Score |
|---|---:|
| Gold Joker | +10.00 |
| Silver Joker | +3.00 |
| Bronze Joker | +1.00 |
| Banned component | -12.00 |
| Matching Planet / permanent hand level gained | +0.50 per level |
| Strategy-directed Tarot use | +0.30 per use |
| Strategy-directed Spectral use | +0.50 per use |
| Matching enhancement in current deck | +0.35 per card |

Legacy Red/White statuses are `Candidate = 1.5`, `Highlighted = 3.5`, `Committed = 10.0`, and `Mature = 20.0`. These thresholds are **not the final target rank system**. They remain runtime compatibility values until track-rank geometry is introduced and calibrated.

Gold = defining/very strong contribution after prerequisites. Silver = material support. Bronze = weak/conditional contribution. Banned = explicit mechanical contradiction. Universal Joker value remains a separate axis.

## Migration interpretation

Read every row as:

```text
component -> contribution to this strategy track
```

not:

```text
component -> vote that this must become the one global strategy
```

Parent/child factoring still prevents duplicate evidence. Cross-track synergy belongs in the composition graph. A component may legitimately occur in multiple unrelated tracks when it advances each for a different mechanical reason.

The detailed relationship tables from the current runtime continue below in the repository history/current implementation and must be preserved during migration. Before changing a row, verify the live runtime relationship and deterministic tests; after migration, recalibrate contribution weights/rank thresholds from unchanged-HEAD five-run telemetry rather than arbitrary score inflation.

## Immediate relationship audit required during migration

The existing large table predates the combined-build decision and contains rows whose **legacy support meaning must be re-audited** under the new semantics. Highest-priority audit targets:

1. Burnt Joker entries across poker-hand tracks: distinguish `compatible hand plan` from `Burnt power-engine contribution`; do not let repeated copies imply that Burnt belongs independently to every hand track.
2. Green/Burglar entries across High Card/Pair: they may support those hand shapes while also forming a Green/no-discard engine, but must never be composed with Burnt.
3. Scholar/Aces/DNA: preserve strong Aces contribution and multi-track value; do not require Aces to displace Burnt to make Scholar worth buying.
4. Ride the Bus/no-face: ensure contribution creates the no-face execution prescription, not merely a score.
5. Ten-Four: Walkie alone is not a Gold-quality complete route; the paired Walkie + Even structure is the meaningful package.
6. Throwback: unscaled x1.0 is not mature Gold realized evidence; realized skip scaling matters.
7. All `generic support requires X commitment` clauses: migrate away from legacy global commitment toward `track sufficiently developed / prerequisite present` semantics.

## Detailed current relationship dataset

**Important:** The branch's pre-migration detailed dataset is intentionally retained in Git history at commit `5bcc8fbbfc6afe97b544d75a3c10041a16b2d02e` (blob) and in runtime catalogue/tests. During implementation, regenerate this document's detailed tables from the runtime catalogue rather than hand-maintaining two divergent 37k-character copies. The target is for runtime data to become authoritative and this document to become a generated/audited view.

Until that generator exists, consult the runtime catalogue plus the immediately preceding version of this file for the complete row-by-row matrix. Do **not** infer missing rows from this abbreviated migration header.
