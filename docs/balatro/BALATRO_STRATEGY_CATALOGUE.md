# Balatro Strategy Catalogue

Canonical catalogue after **Catalogue Audit Pass 3** plus one post-freeze mechanical correction. Architecture rules live in `BALATRO_STRATEGY_SYSTEM.md`; exact weights and audited threshold geometry live in `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Audit status

Implementation produced 50 candidate Bonds. Pass 1 pruned six weak/non-independent axes. Pass 2 corrected contributor overlap/misclassification. Pass 3 audited R1-R5 authority and fixed unreachable R4/R5 ceilings. A post-freeze mechanical review identified one genuine missing inverse-payoff axis: **No Face Cards**, defined by Ride the Bus. **Accepted count is now frozen at 45 pending runtime telemetry evidence.**

A Bond is a persistent, independently developable strategic axis. Components may contribute to multiple Bonds only when they genuinely develop each axis; overlap never becomes additive score power.

## State vocabulary

```text
LOCKED = defining prerequisite absent
R0     = valid naturally available Bond below R1
R1     = emerging / recognized
R2     = established enough to reinforce deliberately
R3     = committed development
R4     = power-engine-capable authority for that axis
R5     = capstone / extreme legitimate commitment
```

Rank = development. Realization = whether the engine functions. Build Health = whether it actually survives/scales. R5 does not guarantee a win.

## Accepted Bonds

1. **Burnt** — Burnt-Joker-defined permanent hand-level specialization. Hard unlock: Burnt Joker. Target comes from strongest compatible poker-hand Bond; High Card fallback.
2. **Held Cards** — direct payoff from intentionally retained cards. Baron/Shoot the Moon/Raised Fist/Steel/hand capacity. Mime, Gold Cards and Blue Seals excluded.
3. **Held Retrigger** — repeated held-card effects. Mime principal contributor; separate from Held Cards.
4. **Steel** — persistent Steel-card density and Steel-specific payoff.
5. **Pair** — Pair specialization.
6. **High Card** — High Card specialization.
7. **Aces** — Ace density/payoff.
8. **No-Discard** — value from deliberately avoiding discards.
9. **Cash** — bankroll as persistent economy/scoring infrastructure.
10. **Lucky** — Lucky-card density/payoff/scaling.
11. **Glass** — Glass density/payoff/scaling.
12. **Face Cards** — face-card density/payoff.
13. **Two Pair** — Two Pair specialization.
14. **Three of a Kind** — Three-of-a-Kind specialization.
15. **Four of a Kind** — Four-of-a-Kind specialization. Flower Pot is excluded from quota.
16. **Straight** — Straight specialization.
17. **Flush** — Flush specialization plus suit-density infrastructure.
18. **Played Retrigger** — retriggering played/scoring cards; separate from Held Retrigger.
19. **Stone** — Stone density/creation/payoff.
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
32. **Low Ranks (2-5)** — 2-5 rank-family specialization. Walkie-Talkie remains weak support.
33. **Kings** — King density/payoff; Baron/Triboulet support.
34. **Queens** — Queen density/payoff; Shoot the Moon/Triboulet support.
35. **Jacks** — Hit-the-Road-centered Jack specialization. Density alone has low authority; extreme concentration plus the defining payoff can reach capstone.
36. **Tarot** — persistent Tarot-generation/access deck-shaping engine. Structural/resource Bond, not direct scoring power.
37. **Planet** — persistent Planet-generation/access hand-level engine. Prescriptions must reinforce relevant poker-hand Bonds rather than indiscriminate Planet acquisition.
38. **Discard** — discard-payoff axis. Hard unlock requires Yorick/Castle/Mail-In Rebate/Faceless Joker/Hit the Road; Burnt and extra capacity only deepen it after unlock.
39. **Blind Skip** — Throwback-defined skip-scaling axis. Diet Cola/support history cannot establish it.
40. **Sell Value** — Swashbuckler-defined sell-value scoring axis. Egg/Gift Card/sell-value state deepen it.
41. **Joker Sacrifice** — Dagger/Madness-defined sacrifice scaling. Riff-Raff/history support only after unlock.
42. **Card Destruction** — current destruction payoff/engine. Historical reduction after engine loss belongs to Deck Thinning.
43. **Hand Repetition** — Card Sharp/Supernova-defined repeated-hand payoff. Play-count history alone never creates it.
44. **Enhanced Cards** — Driver's-License-defined enhanced-density XMult axis. Generic enhancement density alone is not a Bond.
45. **No Face Cards** — Ride-the-Bus-defined avoidance/scaling axis. Hard unlock: Ride the Bus. Natural J/Q/K depletion develops the Bond because it reduces reset risk. Generic face-card interaction does not contribute. Explicit conflict: Face Cards.

## Removed / demoted mechanics

```text
Tens        -> Low Ranks/card-rank support
Wild Cards  -> suit/flush/tactical support
Mult Cards  -> enhancement/card valuation support
Bonus Cards -> enhancement/card valuation support
Spectral    -> consumable/tactical transformation
Hand Size   -> Held Cards/draw/tactical support
Flower Pot  -> tactical/motif valuation, not Four-of-a-Kind quota
```

## Sparse relationships

```text
Burnt x No-Discard                 = CONFLICT
Discard x No-Discard               = CONFLICT
Face Cards x No Face Cards         = CONFLICT
Burnt <-> Discard                  = SYNERGY
Held Cards <-> Held Retrigger      = SYNERGY
Held Cards <-> Steel               = SYNERGY
Held Retrigger <-> Steel           = SYNERGY
Card Destruction <-> Deck Thinning = SYNERGY
```

All unlisted pairs default to neutral. Complex super-additive packages belong to motifs.

## Composition motif example

```text
Held Cards + Held Retrigger + Steel + Kings
    -> Baron-Mime-Steel motif
```

## Audit Pass 3 conclusions

- The implementation-pass catalogue contained several Bonds whose mathematical contribution ceiling could never reach R4 or R5. Those ceilings were corrected rather than leaving decorative unreachable ranks.
- Early/mid contribution bands remain conservative. High-end permanent poker-hand, suit and rank concentration now gains additional authority only at extreme investment.
- Complete Held Cards, Held Retrigger, Steel, Lucky, Glass, Stone, Gold Economy and several defining-payoff engines can now reach R5 through legitimate near-complete packages.
- Deck Thinning and Deck Growth now recognize extreme persistent structure more strongly without treating raw deck size as direct score power.
- Tarot can reach R5 only with essentially full infrastructure; Planet retains the higher original capstone threshold.
- Shared implementation-pass threshold dictionaries are not allowed to cross-mutate audited siblings; `authority_calibration.py` rebinds per-Bond tables and tests this explicitly.
- No Face Cards was added after freeze only because it was a discovered mechanical omission, not speculative catalogue expansion.

## Freeze status / next work

The **45-Bond catalogue, contributor classification and rank-authority geometry are now frozen for implementation**. Changes from here should require either a discovered mechanical error or runtime telemetry evidence rather than further speculative catalogue expansion.

Next architecture stage:

```text
1. define realization rules per Bond
2. evaluate all Bonds + realization together
3. implement sparse relationship consumption
4. implement composition motifs, beginning with Baron-Mime-Steel
5. compose a combined build / power engine
6. connect score projection + Build Health
7. only then migrate live strategy authority away from legacy Primary/Secondary/Third
```
