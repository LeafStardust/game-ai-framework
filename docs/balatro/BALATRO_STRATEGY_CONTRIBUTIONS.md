# Balatro Strategy Contributions

Canonical component/state -> Bond contribution values after **Catalogue Audit Pass 3**. Architecture is in `BALATRO_STRATEGY_SYSTEM.md`; identities/unlocks are in `BALATRO_STRATEGY_CATALOGUE.md`.

## Rules

- One shared weighted pool per Bond; contributors are additive alternatives, never sequential rank keys.
- Rank measures development only; realization and Build Health remain separate.
- Multi-Bond contribution is intentional only when a component genuinely develops each axis.
- Hard-unlock Bonds return `LOCKED` when the defining payoff is absent; support/history cannot manufacture the Bond.
- Generic enabling mechanics do not receive quota merely because they can participate in a hand.
- R1-R5 authority is calibrated so ordinary support remains low-rank, while legitimate extreme commitment can actually reach R4/R5.
- Values remain provisional for telemetry calibration, but the catalogue/rank geometry is now frozen pending runtime evidence.

## Shared audited structural bands

Poker-hand permanent level contribution for normal/advanced hand Bonds:

```text
level 2-3   +1
level 4-6   +3
level 7-10  +5
level 11-15 +8
level 16-24 +12
level 25+   +18
```

Burnt keeps its own target-hand contribution curve (`+1/+3/+5/+7`) because Burnt already has a defining-Joker unlock and separate contribution geometry.

Suit-density contribution for Hearts/Spades/Clubs/Diamonds:

```text
13/17/21/26/32/40/46/50+ cards = +1/+3/+5/+7/+9/+13/+17/+21
```

Rank-density contribution for Kings/Queens/Jacks:

```text
4/6/9/13/18/24/32/40/44+ cards = +1/+3/+5/+7/+9/+13/+17/+21/+23
```

The high-end bands are intentionally extreme: they make capstone rank attainable without allowing ordinary density to masquerade as a mature build.

## Bonds 1-12

**Burnt** `8/12/17/23/30` — hard unlock Burnt Joker. Burnt +8; Blueprint +5; Brainstorm +5; Telescope +4; Space Joker +2; Blue Seals 1/2/3/4+ = +1/+3/+5/+6; target-hand level 2-3/4-6/7-10/11+ = +1/+3/+5/+7; extra discards above 3 = +1 each, +3 cap.

**Held Cards** `4/8/13/18/22` — Baron +6; Shoot the Moon +4; Raised Fist +2; Steel cards 1/2-3/4-5/6+ = +1/+3/+5/+7; hand size above 8 = +1 each, +3 cap. Mime/Gold/Blue excluded.

**Held Retrigger** `4/8/13/17/21` — Mime +6; Red Seals 1/2-3/4-5/6+ = +1/+3/+5/+7; Blueprint +4 and Brainstorm +4 only with Mime.

**Steel** `4/8/13/17/20` — Steel Joker +5; Steel cards 1/2-3/4-5/6-9/10+ = +1/+3/+6/+9/+12; Red-Seal Steel 1/2-3/4+ = +1/+2/+3.

**Pair** `4/8/13/19/26` — The Duo +6; Jolly +4; Sly +4; Half Joker +2; audited poker-hand level bands.

**High Card** `4/8/13/19/26` — Stuntman +6; Half Joker +3; audited poker-hand level bands.

**Aces** `4/8/13/17/20` — Scholar +6; Fibonacci +3; Ace density 4/6/8/12+ = +1/+3/+5/+7; DNA +4 only with at least 6 Aces.

**No-Discard** `4/8/13/18/22` — Green +6; Burglar +6; Delayed Gratification +4; Ramen +4; Banner +2.

**Cash** `4/9/15/22/30` — Bull +5; Bootstraps +5; Rocket +4; Golden Joker +3; To the Moon +3; Satellite +3; Reserved Parking +2; bankroll $25/$50/$100/$150+ = +1/+3/+5/+7.

**Lucky** `4/8/12/15/17` — Lucky Cat +6; Oops! All 6s +4; Lucky cards 1/3/6/10+ = +1/+3/+5/+7.

**Glass** `4/8/12/16/19` — Glass Joker +6; Glass cards 1/3/6/10+ = +1/+3/+5/+7; destroyed Glass while Glass Joker owned 1/3/6/10+ = +1/+2/+4/+6.

**Face Cards** `4/9/15/22/30` — Pareidolia +6; Sock and Buskin +5; Photograph +4; Scary Face +4; Smiley Face +4; Business Card +2; face density 12/16/20/26+ = +1/+3/+5/+7.

## Bonds 13-22

**Two Pair** `4/8/13/19/26` — Spare Trousers +7; Jolly +2; Sly +2; audited poker-hand level bands.

**Three of a Kind** `4/8/13/19/26` — The Trio +6; Zany +4; Wily +4; audited poker-hand level bands.

**Four of a Kind** `4/8/13/19/26` — The Family +7; Mad +4; Clever +4; audited poker-hand level bands. Flower Pot contributes `0` and belongs to tactical/motif valuation.

**Straight** `4/8/13/19/26` — The Order +6; Crazy +4; Devious +4; Shortcut +5; Four Fingers +3; Runner +4; audited poker-hand level bands.

**Flush** `4/8/13/19/26` — The Tribe +6; Droll +4; Crafty +4; Smeared +5; Four Fingers +3; audited poker-hand level bands; dominant-suit density 16/20/24/30+ = +1/+3/+5/+7.

**Played Retrigger** `4/8/14/21/29` — Sock and Buskin +6; Hack +6; Hanging Chad +6; Dusk +4; Red Seals 1/2/4/7+ = +1/+3/+5/+7.

**Stone** `4/8/13/17/20` — Stone Joker +6; Marble Joker +5; Stone cards 1/3/6/10+ = +1/+3/+6/+9.

**Gold Economy** `4/8/13/17/21` — Golden Ticket +5; Midas Mask +5; Reserved Parking +2; Gold cards 1/3/6/10+ = +1/+3/+6/+9.

**Deck Thinning** `4/7/10/13/16` — Trading Card +5; Sixth Sense +4; permanent reduction from 52: 4/8/12/18+ removed = +1/+3/+5/+7. Extreme persistent thinning alone can reach R2; capstone requires active thinning infrastructure plus deep reduction.

**Deck Growth** `4/7/12/18/25` — Certificate +5; DNA +6; Marble Joker +3; Hologram +4; growth above 52: +4/+8/+12/+18 cards = +1/+3/+5/+7.

## Bonds 23-35

**Full House** `4/8/13/19/22` — The Duo +2; The Trio +2; audited poker-hand level bands.

**Straight Flush** `4/8/13/19/26` — Four Fingers +4; Shortcut +3; Smeared +3; audited poker-hand level bands.

**Five of a Kind** `4/8/13/19/26` — DNA +4; max rank concentration 5/7/10/14+ = +2/+4/+6/+8; audited poker-hand level bands.

**Flush House** `4/8/13/19/23` — Smeared +3; Duo +1; Trio +1; audited poker-hand level bands.

**Flush Five** `4/8/13/19/26` — DNA +3; Smeared +2; same-rank/same-suit concentration 5/7/10+ = +3/+5/+7; audited poker-hand level bands.

**Hearts** `4/9/15/22/30` — Bloodstone +7; Lusty +4; audited Hearts-density bands.

**Spades** `4/9/15/22/30` — Arrowhead +6; Wrathful +4; audited Spades-density bands.

**Clubs** `4/9/15/22/30` — Onyx Agate +6; Gluttonous +4; audited Clubs-density bands.

**Diamonds** `4/9/15/22/30` — Rough Gem +6; Greedy +4; audited Diamonds-density bands.

**Low Ranks (2-5)** `4/9/15/22/30` — Hack +6; Wee Joker +6; Fibonacci +5; Even Steven +3; Walkie-Talkie +2; 2-5 density 16/20/24/30+ = +1/+3/+5/+7.

**Kings** `4/9/15/22/30` — Baron +7; Triboulet +6; audited King-density bands.

**Queens** `4/9/15/22/30` — Shoot the Moon +6; Triboulet +5; audited Queen-density bands.

**Jacks** `4/9/15/22/30` — Hit the Road +7; audited Jack-density bands. Extreme density + Hit the Road can reach capstone; ordinary Jack density remains low authority.

## Bonds 36-44

**Tarot** `4/9/15/22/28` — Cartomancer +6; Vagabond +5; Hallucination +4; Fortune Teller +4; Tarot Merchant +4; Tarot Tycoon +6. All major infrastructure together can reach R5; one access component stays low-rank.

**Planet** `4/9/15/22/30` — Constellation +6; Astronomer +4; Space Joker +3; Telescope +5; Planet Merchant +4; Planet Tycoon +6; Blue Seals 1/2/4/7+ = +1/+3/+5/+7.

**Discard** `4/9/15/22/30` — hard unlock Yorick/Castle/Mail-In Rebate/Faceless Joker/Hit the Road. Yorick +7; Castle +5; Mail-In Rebate +4; Faceless Joker +4; Hit the Road +3; Burnt +3 after unlock; extra discards above 3 = +1 each, +4 cap.

**Blind Skip** `4/8/12/15/18` — hard unlock Throwback. Throwback +7; Diet Cola +4 after unlock; skips 1/3/5/8+ = +1/+3/+5/+7.

**Sell Value** `4/9/15/20/25` — hard unlock Swashbuckler. Swashbuckler +7; Gift Card +6; Egg +5; total Joker sell value $10/$20/$35/$60+ = +1/+3/+5/+7.

**Joker Sacrifice** `4/9/14/18/23` — hard unlock Ceremonial Dagger or Madness. Dagger +7; Madness +6; Riff-Raff +3 after unlock; destroyed Jokers 1/3/6/10+ = +1/+3/+5/+7.

**Card Destruction** `4/9/15/20/26` — requires current Canio/Trading Card/Sixth Sense/Glass Joker engine. Canio +7; Trading Card +5; Sixth Sense +4; Glass Joker +3; cards destroyed 2/5/10/16+ = +1/+3/+5/+7.

**Hand Repetition** `4/8/13/16/20` — hard unlock Card Sharp or Supernova. Card Sharp +7; Supernova +6; max relevant hand-play count 5/10/18/30+ = +1/+3/+5/+7.

**Enhanced Cards** `4/8/13/16/20` — hard unlock Driver's License. Driver's License +7; Midas Mask +3; Marble Joker +3; enhanced density 8/12/16/24+ = +1/+3/+5/+7.

## Audit Pass 3 authority conclusions

- A single ordinary contributor should normally produce R0/R1, not mature authority.
- R2 means there is enough persistent structure to reinforce deliberately.
- R3 means committed development.
- R4 means the Bond may legitimately influence power-engine selection.
- R5 must be reachable, but only by a near-complete or extreme legitimate package.
- High-end permanent hand/suit/rank investment now has additional bands because the implementation-pass caps made several R4/R5 states mathematically impossible.
- Threshold tables for Bonds that shared implementation aliases are rebound independently in `authority_calibration.py`; changing one audited Bond must not silently recalibrate its siblings.
- Rank still does not equal score. A structurally R5 Bond can remain weak or unrealized; Build Health and score projection decide survival.

## Removed candidate mappings

```text
Tens        -> Low Ranks/card-rank support
Wild Cards  -> suit/flush/Flower Pot/card valuation support
Mult Cards  -> enhancement/card valuation support
Bonus Cards -> enhancement/card valuation support
Spectral    -> consumable/tactical transformation layer
Hand Size   -> Held Cards / draw-consistency / tactical support
Flower Pot  -> tactical/motif valuation; no Four-of-a-Kind quota
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
