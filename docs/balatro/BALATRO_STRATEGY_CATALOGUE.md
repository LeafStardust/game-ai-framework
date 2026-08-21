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

Rank measures development. Realization (`DORMANT/PARTIAL/ACTIVE/MATURE`) measures whether that development is functioning. Build Health measures whether it is actually strong enough.

## Accepted Bonds

### 1. Burnt
Defining-Joker Bond for deliberate permanent specialization of a chosen poker hand through first-discard leveling. Hard unlock: Burnt Joker. Target hand comes from the strongest compatible poker-hand Bond; fallback is High Card. Explicit conflict: No-Discard.

### 2. Held Cards
Cards intentionally retained for direct held-card payoff. No hard unlock. Current direct contributors: Baron, Shoot the Moon, Raised Fist, Steel density, extra hand size. **Mime, Gold Cards, and Blue Seals do not add Held Cards quota.**

### 3. Held Retrigger
Retriggering held-card effects. Mime is the principal direct contributor; Red Seals and copy-Joker support can deepen it. Separate from Held Cards. Explicit synergy: Held Cards and Steel.

### 4. Steel
Persistent Steel-card density and Steel-specific payoff. Separate from Held Cards and Held Retrigger but synergizes with both.

### 5. Pair
Poker-hand specialization around Pair. Permanent Pair levels and Pair-specific Jokers contribute.

### 6. High Card
Poker-hand specialization around High Card. Permanent High Card levels and High-Card-specific Jokers contribute.

### 7. Aces
Rank-specialization Bond centered on Ace density and Ace payoffs such as Scholar. DNA may bridge when it is actually supporting Ace concentration.

### 8. No-Discard
Zero/low-discard execution built around Green Joker, Burglar and other no-discard payoffs. Explicit conflict: Burnt.

### 9. Cash
Money as strategic infrastructure and, when relevant, direct scoring power. Includes Bull/Bootstraps and economy/scaling support. Build Health remains responsible for deciding when cash must be spent for survival.

### 10. Lucky
Lucky-card density and Lucky-specific payoff/scaling.

### 11. Glass
Glass-card density and Glass-specific payoff. Realization must eventually account for break risk and whether Glass is actually used as scoring payoff rather than wasted.

### 12. Face Cards
Face-card density and face-specific payoff. This is distinct from individual rank Bonds such as Aces. Boss suppression affects realization, not development.

### 13. Two Pair
Poker-hand specialization around Two Pair. Spare Trousers is a major contributor; permanent Two Pair levels contribute.

### 14. Three of a Kind
Poker-hand specialization around Three of a Kind, including The Trio and matching hand-level investment.

### 15. Four of a Kind
Poker-hand specialization around Four of a Kind, including The Family and matching hand-level investment. Flower Pot is temporarily treated as a minor contributor per catalogue direction; audit this classification later because its mechanic is not intrinsically Four-of-a-Kind-only.

### 16. Straight
Poker-hand specialization around Straights. Shortcut, Four Fingers, Runner and Straight-specific scoring Jokers contribute.

### 17. Flush
Poker-hand specialization around Flushes. Suit density, Smeared Joker, Four Fingers and Flush-specific scoring Jokers contribute.

### 18. Played Retrigger
Retriggering played/scoring cards. Sock and Buskin, Hack, Hanging Chad, Dusk and Red-Seal played-card infrastructure contribute. This is separate from Held Retrigger.

### 19. Stone
Stone-card density and Stone-specific creation/payoff, including Stone Joker and Marble Joker.

### 20. Gold Economy
Gold-card-specific economy. Golden Ticket, Midas Mask and actual Gold-card density contribute. Gold Cards do **not** add Held Cards quota merely because their ordinary economy trigger occurs while held.

### 21. Deck Thinning
Persistent reduction/concentration of the playing-card deck. Trading Card, Sixth Sense and actual permanent reduction contribute. Removal only helps when it improves the combined build; Build Health/transition logic remains authoritative.

### 22. Deck Growth
Persistent addition of playing cards as a strategic engine. DNA, Certificate, Marble Joker, Hologram and actual permanent deck growth contribute. Added-card quality is still evaluated separately; raw bloat is not automatically good.

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
- Production Primary/Secondary/Third strategy selection is still legacy migration infrastructure and should not be half-replaced before the full Bond composer is ready.

## Audit note

This file records implementation-pass truth, not final calibration truth. After all Bonds are implemented, perform a full independent catalogue audit for misclassified contributors, duplicated Bonds, missing synergies/conflicts, weak/pointless Bonds, and threshold distortion before production integration.
