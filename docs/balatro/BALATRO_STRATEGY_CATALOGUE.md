# Balatro Strategy Catalogue

Canonical catalogue after **Catalogue Audit Pass 2**. Architecture rules live in `BALATRO_STRATEGY_SYSTEM.md`; exact weights live in `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Audit status

Implementation produced 50 candidates. Pass 1 pruned six weak/non-independent axes. Pass 2 audited contributor overlap and narrow/resource Bonds. **Current accepted count remains 44.** Flower Pot was removed from Four-of-a-Kind quota; Jacks, Tarot and Planet survive with narrower authority.

A Bond is a persistent, independently developable strategic axis. Components may contribute to multiple Bonds only when they genuinely develop each axis; overlap never becomes additive score power.

## State vocabulary

```text
LOCKED = defining prerequisite absent
R0     = valid naturally available Bond below R1
R1-R5  = increasing development
```

Rank = development. Realization = whether the engine functions. Build Health = whether it actually survives/scales.

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
15. **Four of a Kind** — Four-of-a-Kind specialization. Flower Pot is explicitly excluded from quota after Pass 2; it is generic four-suit payoff, not Four-of-a-Kind development.
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
35. **Jacks** — Hit-the-Road-centered Jack specialization. Retained: the defining payoff creates a real rank-specific deck-shaping loop. Density alone has low authority.
36. **Tarot** — persistent Tarot-generation/access deck-shaping engine. Structural/resource Bond, not direct scoring power.
37. **Planet** — persistent Planet-generation/access hand-level engine. Prescriptions must reinforce relevant poker-hand Bonds rather than indiscriminate Planet acquisition.
38. **Discard** — discard-payoff axis. Hard unlock requires Yorick/Castle/Mail-In Rebate/Faceless Joker/Hit the Road; Burnt and extra capacity only deepen it after unlock.
39. **Blind Skip** — Throwback-defined skip-scaling axis. Diet Cola/support history cannot establish it.
40. **Sell Value** — Swashbuckler-defined sell-value scoring axis. Egg/Gift Card/sell-value state deepen it.
41. **Joker Sacrifice** — Dagger/Madness-defined sacrifice scaling. Riff-Raff/history support only after unlock.
42. **Card Destruction** — current destruction payoff/engine. Historical reduction after engine loss belongs to Deck Thinning.
43. **Hand Repetition** — Card Sharp/Supernova-defined repeated-hand payoff. Play-count history alone never creates it.
44. **Enhanced Cards** — Driver's-License-defined enhanced-density XMult axis. Generic enhancement density alone is not a Bond.

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

## Audit Pass 2 conclusions

- Flower Pot was a real misclassification and is removed from Four of a Kind.
- Multi-Bond components are retained where mechanically genuine; structural overlap is intentional and does not imply score double-counting.
- Advanced poker hands may receive low-weight support from mechanics that genuinely increase their feasibility.
- Jacks survives because Hit the Road supplies a defining payoff and reason to reshape the deck around Jacks.
- Tarot and Planet survive as resource/development Bonds, but their rank authority is constrained to deck shaping/hand leveling; they are not automatically power engines.
- No additional Bond was admitted in Pass 2.

## Next work

Run the affected focused tests. If green, Audit Pass 3 should inspect **rank-threshold geometry and R1-R5 authority** across all 44 Bonds, then freeze the catalogue/contribution model before implementing realization and composition motifs.
