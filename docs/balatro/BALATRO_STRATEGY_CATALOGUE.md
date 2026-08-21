# Balatro Strategy Catalogue

Canonical catalogue of Balatro strategy tracks (Bonds). Architecture rules live in `BALATRO_STRATEGY_SYSTEM.md`; numeric contribution data lives in `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Status

Implementation pass in progress. The catalogue is being built in batches and will receive a deliberate full audit after all Bonds are implemented. Legacy strategy-tree and Gold/Silver/Bronze data are migration evidence only.

## State vocabulary

```text
LOCKED = defining prerequisite absent; Bond does not exist yet
R0     = naturally available Bond below first development threshold
R1-R5  = increasing development
```

Rank measures development. Realization (`DORMANT/PARTIAL/ACTIVE/MATURE`) measures whether that development is functioning. Build Health measures whether it is actually strong enough. Contributors are alternative/additive paths into one Bond meter; they are not sequential rank recipes.

## Accepted Bonds

### 1. Burnt
Defining-Joker Bond for deliberate permanent specialization of a chosen poker hand through first-discard leveling. Hard unlock: Burnt Joker. Target comes from the strongest compatible poker-hand Bond, with High Card fallback. Conflict: No-Discard.

### 2. Held Cards
Direct held-card payoff. Contributors include Baron, Shoot the Moon, Raised Fist, Steel density and extra hand size. Mime, Gold Cards and Blue Seals add zero Held Cards quota.

### 3. Held Retrigger
Retriggering held-card effects. Mime is principal direct contributor; Red Seals and Mime-copy support deepen it. Synergy: Held Cards and Steel.

### 4. Steel
Persistent Steel-card density and Steel-specific payoff. Separate from Held Cards/Held Retrigger while synergizing with both.

### 5. Pair
Poker-hand specialization around Pair.

### 6. High Card
Poker-hand specialization around High Card.

### 7. Aces
Ace density and Ace-specific payoff, with conditional DNA bridge support.

### 8. No-Discard
Zero/low-discard execution around Green Joker, Burglar and related payoff. Conflict: Burnt.

### 9. Cash
Money as strategic infrastructure/direct scoring when relevant. Build Health still decides when survival requires spending.

### 10. Lucky
Lucky-card density and Lucky-specific payoff/scaling.

### 11. Glass
Glass-card density and Glass-specific payoff/scaling.

### 12. Face Cards
Face-card density and face-specific payoff. Boss suppression affects realization, not development.

### 13. Two Pair
Poker-hand specialization around Two Pair; Spare Trousers is a major contributor.

### 14. Three of a Kind
Poker-hand specialization around Three of a Kind.

### 15. Four of a Kind
Poker-hand specialization around Four of a Kind. Flower Pot remains a provisional minor contributor only and is explicitly flagged for audit because its mechanic is broader than Four of a Kind.

### 16. Straight
Poker-hand specialization around Straights.

### 17. Flush
Poker-hand specialization around Flushes, including suit-density infrastructure.

### 18. Played Retrigger
Retriggering played/scoring cards. Separate from Held Retrigger.

### 19. Stone
Stone-card density and Stone-specific creation/payoff.

### 20. Gold Economy
Gold-card-specific economy. Gold Cards do not add Held Cards quota merely because they trigger while held.

### 21. Deck Thinning
Persistent playing-card removal/concentration. Removal is valuable only when it improves the combined build.

### 22. Deck Growth
Persistent addition of playing cards as an engine. Added-card quality remains a separate composition/Build Health concern.

### 23. Full House
Poker-hand specialization around Full House. Permanent hand levels are the cleanest direct development; Duo/Trio provide small bridge contribution rather than defining it.

### 24. Straight Flush
Poker-hand specialization around Straight Flush. Four Fingers, Shortcut and Smeared Joker are infrastructure contributors; none is a sequential requirement.

### 25. Five of a Kind
Extreme single-rank concentration. DNA is useful direct growth infrastructure, while actual rank concentration and permanent Five-of-a-Kind levels are persistent development.

### 26. Flush House
Advanced hand specialization requiring compatible suit and pair/trips structure. Smeared/Duo/Trio are low bridge contributors; permanent hand investment can independently establish the Bond.

### 27. Flush Five
Advanced same-rank/same-suit specialization. DNA/Smeared are bridge contributors; actual same-rank same-suit concentration and permanent hand investment carry structural authority.

### 28. Hearts
Suit-specialization Bond. Bloodstone and Lusty Joker are direct contributors; actual Hearts density provides persistent development.

### 29. Spades
Suit-specialization Bond. Arrowhead and Wrathful Joker are direct contributors; actual Spades density provides persistent development.

### 30. Clubs
Suit-specialization Bond. Onyx Agate and Gluttonous Joker are direct contributors; actual Clubs density provides persistent development.

### 31. Diamonds
Suit-specialization Bond. Rough Gem and Greedy Joker are direct contributors; actual Diamonds density provides persistent development.

### 32. Low Ranks (2-5)
Rank-family specialization around 2-5 payoff. Hack, Wee Joker and Fibonacci are strong contributors; Even Steven is moderate. Walkie-Talkie is deliberately only a weak contributor and does **not** define its own Bond.

### 33. Kings
King density and King-specific payoff. Baron is the strongest current contributor; Triboulet also materially develops the axis. This Bond is deliberately separate from Held Cards so Baron can contribute to both without collapsing rank structure into held-card structure.

### 34. Queens
Queen density and Queen-specific payoff. Shoot the Moon is the strongest current contributor; Triboulet also contributes.

### 35. Jacks
Jack density and Jack-specific payoff, currently centered on Hit the Road. This may remain a narrower/weak Bond and is flagged for later audit if its strategic depth proves insufficient.

### 36. Tens
Ten density and Ten-specific payoff. Walkie-Talkie contributes only modestly and does not establish the Bond alone. This prevents the old Walkie-Talkie strategy from reappearing under another label.

### 37. Wild Cards
Wild-card density and suit-flexibility infrastructure. Flower Pot is currently a small contributor because Wild cards directly help its multi-suit requirement. Audit later whether this axis has enough independent authority to survive as a full Bond.

### 38. Mult Cards
Mult-enhancement density as a persistent flat-Mult support axis. Vampire is only a small bridge because it consumes enhancements rather than representing Mult-card commitment. Explicitly audit whether this should remain a full Bond or merge into a broader enhancement/scoring axis.

### 39. Bonus Cards
Bonus-enhancement density as a persistent chip-support axis. No defining Joker is currently required. This is intentionally marked as a weak candidate for the later pruning audit.

### 40. Tarot
Tarot generation/access as a persistent deck-shaping resource engine. Cartomancer, Vagabond, Hallucination, Fortune Teller and Tarot-voucher infrastructure contribute. Rank indicates access/development, not whether any specific Tarot use is correct.

### 41. Planet
Planet generation/access and hand-level infrastructure. Constellation, Astronomer, Space Joker, Telescope, Planet-voucher infrastructure and Blue Seals contribute. This Bond is broader than Burnt: Burnt may use Planet infrastructure, but Planet access exists independently.

### 42. Spectral
Spectral generation/access as a high-impact transformation resource axis. Sixth Sense and Seance are current direct contributors. This is a narrow Bond and is explicitly subject to later audit for depth/authority.

## Sparse relationships currently frozen

```text
Burnt x No-Discard             = CONFLICT
Held Cards <-> Held Retrigger  = SYNERGY
Held Cards <-> Steel           = SYNERGY
Held Retrigger <-> Steel       = SYNERGY
```

Do not add exhaustive pair relationships. Add only mechanically meaningful synergy/conflict edges; super-additive named packages belong in motifs.

## Canonical motif direction

```text
Held Cards + Held Retrigger + Steel + King structure
        -> Baron-Mime-Steel motif
```

Baron itself is not a Bond. Mime itself is not Held Cards. The composition layer combines their Bonds into the power plan.

## Implementation status

- Burnt: dedicated evaluator.
- Held Cards: dedicated evaluator.
- Bonds 3-12: `catalogue_batch_one.py`.
- Bonds 13-22: `catalogue_batch_two.py`.
- Bonds 23-32: `catalogue_batch_three.py`.
- Bonds 33-42: `catalogue_batch_four.py`.
- Production Primary/Secondary/Third strategy selection is still legacy migration infrastructure and should not be half-replaced before the full Bond composer is ready.

## Audit note

This file records implementation-pass truth, not final calibration truth. After all Bonds are implemented, perform a full independent catalogue audit for misclassified contributors, duplicated Bonds, missing synergies/conflicts, weak/pointless Bonds, threshold distortion and Bonds that should be merged or removed before production integration.
