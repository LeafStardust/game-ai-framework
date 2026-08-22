# Balatro Strategy Catalogue

Canonical catalogue after Catalogue Audit Pass 3 plus post-freeze mechanical coverage corrections. Architecture rules live in `BALATRO_STRATEGY_SYSTEM.md`; exact weights live in `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Status

The catalogue is now frozen at **46 Bonds** pending runtime evidence. Post-freeze additions are allowed only for genuine mechanical omissions discovered by Joker-coverage review. No Face Cards and Vampire were admitted under that rule.

Rank vocabulary remains `LOCKED`, `R0`, `R1` Emerging, `R2` Established, `R3` Committed, `R4` Power-engine-capable, `R5` Capstone. Rank is structural development, not score or survival.

## Accepted Bonds

1. Burnt — Burnt-Joker-defined hand-level specialization.
2. Held Cards — payoff from intentionally retained cards.
3. Held Retrigger — repeated held-card effects; Mime-centered.
4. Steel — Steel density and payoff.
5. Pair — Pair specialization.
6. High Card — High Card specialization; Stuntman is a major contributor.
7. Aces — Ace density/payoff.
8. No-Discard — value from avoiding discards.
9. Cash — bankroll economy/scoring infrastructure.
10. Lucky — Lucky-card density/payoff/scaling.
11. Glass — Glass density/payoff/scaling.
12. Face Cards — face-card density/payoff.
13. Two Pair — Two Pair specialization; Square Joker is a low/moderate four-card bridge.
14. Three of a Kind — Three-of-a-Kind specialization.
15. Four of a Kind — Four-of-a-Kind specialization; Flower Pot explicitly gives no quota.
16. Straight — Straight specialization.
17. Flush — Flush specialization plus suit-density infrastructure.
18. Played Retrigger — retriggering played/scoring cards.
19. Stone — Stone density/creation/payoff.
20. Gold Economy — Gold-card-specific economy.
21. Deck Thinning — persistent deck reduction/concentration; Erosion is a major payoff contributor.
22. Deck Growth — persistent card addition as an engine.
23. Full House — Full House specialization.
24. Straight Flush — Straight Flush specialization.
25. Five of a Kind — extreme single-rank concentration.
26. Flush House — suited pair/trips concentration.
27. Flush Five — same-rank/same-suit concentration.
28. Hearts — Hearts specialization.
29. Spades — Spades specialization.
30. Clubs — Clubs specialization.
31. Diamonds — Diamonds specialization.
32. Low Ranks (2-5) — 2-5 rank-family specialization.
33. Kings — King density/payoff.
34. Queens — Queen density/payoff.
35. Jacks — Hit-the-Road-centered Jack specialization.
36. Tarot — persistent Tarot-generation/access deck-shaping engine.
37. Planet — persistent Planet-generation/access hand-level engine.
38. Discard — discard-payoff axis.
39. Blind Skip — Throwback-defined skip-scaling axis.
40. Sell Value — Swashbuckler-defined sell-value scoring axis.
41. Joker Sacrifice — Dagger/Madness-defined sacrifice scaling.
42. Card Destruction — current destruction payoff/engine.
43. Hand Repetition — Card Sharp/Supernova repeated-hand payoff.
44. Enhanced Cards — Driver's-License-defined enhanced-density XMult axis.
45. No Face Cards — Ride-the-Bus-defined avoidance/scaling axis; face depletion develops it.
46. Vampire — Vampire-defined enhancement-consumption scaling axis; enhancement feedstock and renewable creation develop it.

## Joker coverage corrections

- **Square Joker -> Two Pair +3**. Exactly-four-card play strongly aligns with natural Two Pair execution, but Square alone cannot establish Two Pair.
- **Erosion -> Deck Thinning +7**. Erosion directly converts permanent deck reduction into Mult, so it is a major thinning payoff.
- **Vampire -> new Vampire Bond**. Vampire is the hard unlock. Midas Mask is the strongest renewable-feed bridge; current enhanced-card density and accumulated Vampire consumption deepen the Bond.
- Campfire, Obelisk and Flash Card remain intentionally unassigned at Bond level for now; their mechanics are handled tactically/support-side unless later evidence justifies otherwise.

## Sparse relationships

```text
Burnt x No-Discard                 = CONFLICT
Discard x No-Discard               = CONFLICT
Face Cards x No Face Cards         = CONFLICT
Vampire x Enhanced Cards           = CONFLICT
Burnt <-> Discard                  = SYNERGY
Held Cards <-> Held Retrigger      = SYNERGY
Held Cards <-> Steel               = SYNERGY
Held Retrigger <-> Steel           = SYNERGY
Card Destruction <-> Deck Thinning = SYNERGY
```

`Vampire x Enhanced Cards` is a conflict because Driver's License wants enhanced-card density retained while Vampire consumes scoring-card enhancements for permanent scaling.

All unlisted pairs default to neutral. Complex super-additive packages belong to motifs.

## Removed / demoted mechanics

```text
Tens        -> Low Ranks/card-rank support
Wild Cards  -> suit/flush/tactical support
Mult Cards  -> enhancement/card valuation support
Bonus Cards -> enhancement/card valuation support
Spectral    -> consumable/tactical transformation
Hand Size   -> Held Cards/draw/tactical support
Flower Pot  -> tactical/motif valuation
```

## Next stage

Do not expand the catalogue speculatively. Continue the Joker-coverage sweep only to catch clear omissions, then implement realization across all accepted Bonds, followed by relationship consumption, motifs/composer, Build Health/score projection, and finally live-agent migration.
