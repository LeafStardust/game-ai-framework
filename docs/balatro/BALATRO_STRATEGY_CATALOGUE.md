# Balatro Strategy Catalogue

Canonical catalogue of Balatro Bonds after **Catalogue Audit Pass 1**. Architecture rules live in `BALATRO_STRATEGY_SYSTEM.md`; exact weights live in `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Audit status

The implementation-pass catalogue reached 50 candidates. Audit Pass 1 pruned six that failed the Bond-admission test and tightened unlock semantics on several others. **Current accepted count: 44.** This is not final calibration truth; later audit passes may still merge/remove/add entries.

A Bond must be a persistent, independently developable strategic axis. A mechanic that only supports another plan belongs as a contributor/state feature, not as its own Bond.

### Removed in Audit Pass 1

- **Tens** — too narrow; Walkie-Talkie remains weak Low-Ranks support rather than restoring its own strategy.
- **Wild Cards** — suit-flexibility infrastructure, not an independent power plan.
- **Mult Cards** — enhancement trait/support, not an independent strategic axis.
- **Bonus Cards** — enhancement trait/support, not an independent strategic axis.
- **Spectral** — high-impact consumable access is tactical/resource infrastructure, not persistent Bond development.
- **Hand Size** — support capacity; contributes where relevant (for example Held Cards) but has no independent power plan.

## State vocabulary

```text
LOCKED = defining prerequisite absent
R0     = valid naturally available Bond below R1
R1-R5  = increasing development
```

Rank = development. Realization = whether the engine functions. Build Health = whether it actually survives/scales.

## Accepted Bonds

1. **Burnt** — Burnt-Joker-defined permanent hand-level specialization. Hard unlock: Burnt Joker. Target comes from strongest compatible poker-hand Bond; High Card fallback. Conflict: No-Discard.
2. **Held Cards** — direct payoff from intentionally retained cards. Baron/Shoot the Moon/Raised Fist/Steel/hand capacity. Mime, Gold Cards and Blue Seals are excluded.
3. **Held Retrigger** — repeated held-card effects. Mime is principal contributor; separate from Held Cards.
4. **Steel** — persistent Steel-card density and Steel-specific payoff.
5. **Pair** — Pair hand specialization.
6. **High Card** — High Card specialization.
7. **Aces** — Ace density and Ace-specific payoff.
8. **No-Discard** — value from deliberately avoiding discards. Conflict: Burnt and Discard.
9. **Cash** — bankroll as persistent economy/scoring infrastructure.
10. **Lucky** — Lucky-card density and Lucky-specific payoff/scaling.
11. **Glass** — Glass density and Glass-specific payoff/scaling.
12. **Face Cards** — face-card density and face-specific payoff.
13. **Two Pair** — Two Pair specialization.
14. **Three of a Kind** — Three-of-a-Kind specialization.
15. **Four of a Kind** — Four-of-a-Kind specialization. Flower Pot remains provisional minor support pending later audit.
16. **Straight** — Straight specialization.
17. **Flush** — Flush specialization plus suit-density infrastructure.
18. **Played Retrigger** — retriggering played/scoring cards; separate from Held Retrigger.
19. **Stone** — Stone density and Stone creation/payoff.
20. **Gold Economy** — Gold-card-specific economy.
21. **Deck Thinning** — persistent deck reduction/concentration.
22. **Deck Growth** — persistent card addition as an engine.
23. **Full House** — Full House specialization.
24. **Straight Flush** — Straight Flush specialization.
25. **Five of a Kind** — extreme single-rank concentration.
26. **Flush House** — suited pair/trips concentration.
27. **Flush Five** — same-rank/same-suit concentration.
28. **Hearts** — Hearts specialization.
29. **Spades** — Spades specialization.
30. **Clubs** — Clubs specialization.
31. **Diamonds** — Diamonds specialization.
32. **Low Ranks (2-5)** — 2-5 rank-family specialization. Walkie-Talkie stays weak support only.
33. **Kings** — King density/payoff; Baron/Triboulet support.
34. **Queens** — Queen density/payoff; Shoot the Moon/Triboulet support.
35. **Jacks** — Jack specialization centered on Hit the Road. Still narrow; retain for later audit because it has a defining payoff and deck-shaping consequence.
36. **Tarot** — persistent Tarot-generation/access engine for deck shaping.
37. **Planet** — persistent Planet-generation/hand-level infrastructure.
38. **Discard** — discard-payoff axis. Hard unlock requires a non-Burnt discard payoff (Yorick/Castle/Mail-In Rebate/Faceless Joker/Hit the Road). Burnt/extra discard capacity can deepen it only after unlock.
39. **Blind Skip** — Throwback-defined skip-scaling axis. Hard unlock: Throwback. Diet Cola and skip history are support only.
40. **Sell Value** — Swashbuckler-defined sell-value scoring axis. Hard unlock: Swashbuckler. Egg/Gift Card/sell-value state deepen it.
41. **Joker Sacrifice** — Dagger/Madness-defined sacrifice scaling. Hard unlock: Ceremonial Dagger or Madness. Riff-Raff/history are support only.
42. **Card Destruction** — active destruction payoff/engine. Requires a current Canio/Trading Card/Sixth Sense/Glass Joker engine. Historical deck reduction after the engine disappears belongs to Deck Thinning.
43. **Hand Repetition** — Card Sharp/Supernova-defined repeated-hand payoff. Hard unlock: Card Sharp or Supernova. Play-count history alone never creates it.
44. **Enhanced Cards** — Driver's-License-defined enhanced-density XMult axis. Hard unlock: Driver's License. Generic enhancement density without License is not a Bond.

## Sparse relationships currently accepted

```text
Burnt x No-Discard                 = CONFLICT
Discard x No-Discard               = CONFLICT
Burnt <-> Discard                  = SYNERGY
Held Cards <-> Held Retrigger      = SYNERGY
Held Cards <-> Steel               = SYNERGY
Held Retrigger <-> Steel           = SYNERGY
Card Destruction <-> Deck Thinning = SYNERGY
```

All unlisted pairs default to neutral. Do not build an exhaustive relationship matrix.

## Composition motifs

Named/super-additive builds remain above the Bond layer. Canonical example:

```text
Held Cards + Held Retrigger + Steel + Kings
    -> Baron-Mime-Steel motif
```

Baron and Mime are components, not Bonds; the motif is the Currency-Wars-style pinned/combined strategy.

## Implementation status

- Burnt: dedicated evaluator.
- Held Cards: dedicated evaluator.
- Earlier accepted groups remain in `catalogue_batch_one.py` through `catalogue_batch_three.py`.
- Audited rank/resource subset is in `catalogue_batch_four.py`.
- Audited behavior/payoff subset is in `catalogue_batch_five.py`.
- Production Primary/Secondary/Third selection remains migration infrastructure and is not yet replaced.

## Next audit work

Audit Pass 2 should inspect the surviving 44 for contribution correctness and overlap, especially Flower Pot/Four-of-a-Kind, historical-scaler semantics, cross-Bond duplicate contributors, and whether narrow Jacks/Tarot/Planet/resource axes deserve their present authority. Only after catalogue/contribution audit is stable should realization/composer integration begin.
