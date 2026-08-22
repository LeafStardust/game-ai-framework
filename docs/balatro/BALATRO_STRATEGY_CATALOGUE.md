# Balatro Strategy Catalogue

Canonical catalogue of Balatro strategy tracks (Bonds). Architecture rules live in `BALATRO_STRATEGY_SYSTEM.md`; exact provisional contribution values live in `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Status

Implementation pass in progress. The catalogue will receive a deliberate independent audit after all plausible Bonds are implemented. Legacy strategy-tree and Gold/Silver/Bronze data are migration evidence only.

```text
LOCKED = defining prerequisite absent
R0     = naturally available Bond below R1
R1-R5  = increasing structural development
```

Rank is development. Realization measures whether the engine is functioning. Build Health measures whether it is strong enough. Contributors are alternative/additive paths, never sequential rank recipes.

## Accepted Bonds

1. **Burnt** — first-discard permanent hand specialization. Burnt Joker hard-unlocks the Bond; target comes from the strongest compatible poker-hand Bond, with High Card fallback. Conflict: No-Discard. Synergy: Discard.
2. **Held Cards** — direct payoff from intentionally retained cards. Baron, Shoot the Moon, Raised Fist, Steel density and hand size contribute. Mime, Gold Cards and Blue Seals do not.
3. **Held Retrigger** — repeated held-card effects. Mime is principal; Red Seals/copy support deepen it. Synergy: Held Cards, Steel.
4. **Steel** — Steel-card density and Steel-specific held XMult. Synergy: Held Cards, Held Retrigger.
5. **Pair** — Pair poker-hand specialization.
6. **High Card** — High Card poker-hand specialization.
7. **Aces** — Ace density and Ace-specific payoff; DNA is a conditional bridge.
8. **No-Discard** — zero/low-discard execution around Green Joker/Burglar/etc. Conflict: Burnt, Discard.
9. **Cash** — bankroll as economy/scoring infrastructure; Build Health still decides when survival requires spending.
10. **Lucky** — Lucky-card density and Lucky-specific trigger/scaling support.
11. **Glass** — Glass-card density and Glass-specific payoff/scaling.
12. **Face Cards** — face-card density and face-specific payoff; boss suppression affects realization, not development.
13. **Two Pair** — Two Pair specialization; Spare Trousers is major.
14. **Three of a Kind** — Three-of-a-Kind specialization.
15. **Four of a Kind** — Four-of-a-Kind specialization. Flower Pot remains provisional/minor and must be audited.
16. **Straight** — Straight specialization; Shortcut/Four Fingers/Runner infrastructure contributes.
17. **Flush** — Flush specialization plus suit-density infrastructure.
18. **Played Retrigger** — repeated played/scoring-card triggers; separate from Held Retrigger.
19. **Stone** — Stone-card density and Stone creation/payoff.
20. **Gold Economy** — Gold-card-specific economy. Gold does not add Held Cards quota just because it triggers while held.
21. **Deck Thinning** — persistent playing-card removal/concentration. Synergy: Card Destruction.
22. **Deck Growth** — persistent card addition; quality of added cards remains a composition/Build Health concern.
23. **Full House** — Full House specialization; Duo/Trio are bridge contributors.
24. **Straight Flush** — Straight Flush specialization; Four Fingers/Shortcut/Smeared are infrastructure, not gates.
25. **Five of a Kind** — extreme rank concentration plus Five-of-a-Kind hand development.
26. **Flush House** — suited pair+trips advanced-hand specialization.
27. **Flush Five** — same-rank/same-suit advanced-hand specialization.
28. **Hearts** — Hearts density/payoff; Bloodstone is major.
29. **Spades** — Spades density/payoff.
30. **Clubs** — Clubs density/payoff.
31. **Diamonds** — Diamonds density/payoff.
32. **Low Ranks (2-5)** — 2-5 density/payoff. Hack/Wee/Fibonacci are major; Even Steven moderate; Walkie-Talkie weak and never a standalone Bond.
33. **Kings** — King density/payoff. Baron/Triboulet contribute; separate from Held Cards.
34. **Queens** — Queen density/payoff. Shoot the Moon/Triboulet contribute.
35. **Jacks** — Jack density/payoff centered on Hit the Road. Narrow; audit later.
36. **Tens** — Ten density/payoff. Walkie-Talkie is modest and cannot establish it alone.
37. **Wild Cards** — Wild-card density/suit flexibility. Audit whether it deserves full Bond authority.
38. **Mult Cards** — Mult-enhancement density. Weak/merge candidate for audit.
39. **Bonus Cards** — Bonus-enhancement density. Weak/pruning candidate for audit.
40. **Tarot** — Tarot access/generation as deck-shaping infrastructure.
41. **Planet** — Planet access/generation and hand-level infrastructure. Broader than Burnt; Telescope/Blue Seals belong here as well as contributing to Burnt where aligned.
42. **Spectral** — Spectral generation/access. Narrow; audit for depth.
43. **Discard** — active discard-resource/payoff axis. Yorick/Castle/Mail-In Rebate/Faceless/Hit the Road/Burnt contribute. Conflict: No-Discard. Synergy: Burnt.
44. **Blind Skip** — value/scaling from skipping blinds/tags. Throwback is major; Diet Cola and actual skip history contribute. Audit whether history alone deserves structural weight.
45. **Sell Value** — persistent Joker sell-value growth and payoff. Swashbuckler/Gift Card/Egg are core contributors.
46. **Hand Size** — strategic hand-capacity development. Troubadour/Juggler/Turtle Bean plus actual hand-size growth contribute. Separate from Held Cards so capacity can support other plans too.
47. **Joker Sacrifice** — scaling/value from destroying or consuming Jokers. Ceremonial Dagger/Madness are major; Riff-Raff can provide fodder infrastructure.
48. **Card Destruction** — playing-card destruction as scaling/concentration infrastructure. Canio/Trading Card/Sixth Sense/Glass Joker and destruction history contribute. Synergy: Deck Thinning.
49. **Hand Repetition** — repeated use of one poker hand as an engine. Card Sharp/Supernova and sustained hand-use history contribute.
50. **Enhanced Cards** — broad enhanced-card density/infrastructure. Driver's License is major; Midas/Marble are creation bridges. Audit whether this should remain broad or be absorbed by specific enhancement Bonds.

## Sparse relationships currently frozen

```text
Burnt x No-Discard             = CONFLICT
Discard x No-Discard           = CONFLICT
Burnt <-> Discard              = SYNERGY
Held Cards <-> Held Retrigger  = SYNERGY
Held Cards <-> Steel           = SYNERGY
Held Retrigger <-> Steel       = SYNERGY
Card Destruction <-> Deck Thinning = SYNERGY
```

All unlisted pairs default to `NEUTRAL`. Do not build an exhaustive relationship matrix. Super-additive named packages belong to motifs.

## Canonical motif direction

```text
Held Cards + Held Retrigger + Steel + King structure
        -> Baron-Mime-Steel motif
```

Baron is not a Bond. Mime is not Held Cards. The composition layer combines Bonds into the actual strategy.

## Implementation status

- Burnt: `burnt.py`
- Held Cards: `held_cards.py`
- Bonds 3-12: `catalogue_batch_one.py`
- Bonds 13-22: `catalogue_batch_two.py`
- Bonds 23-32: `catalogue_batch_three.py`
- Bonds 33-42: `catalogue_batch_four.py`
- Bonds 43-50: `catalogue_batch_five.py`

Production Primary/Secondary/Third selection remains legacy migration infrastructure. Do not half-wire the new catalogue into live authority before the catalogue, audit, composer, realization, motifs and integration are ready.

## Audit requirement

After implementation, re-check the entire catalogue from scratch for misclassified contributors, duplicated/overlapping Bonds, weak Bonds that should be removed/merged, missing sparse relationships, incorrect thresholds, state fields that do not exist in telemetry, and motifs that should sit above Bonds rather than inside them.
