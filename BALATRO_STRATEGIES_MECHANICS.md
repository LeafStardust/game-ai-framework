# Balatro Strategy Catalogue — Mechanics

> Concrete universal mechanic-specific strategy definitions.
>
> These are documentation groupings only. At runtime every strategy is a peer in the same universal strategy pool. See [`BALATRO_STRATEGY_PLAYBOOKS.md`](BALATRO_STRATEGY_PLAYBOOKS.md) for architecture and lifecycle rules.

---

## Face Cards

**Identity:** preserve/create Jacks, Queens, and Kings and exploit face-card triggers.

### Gold
- Major face-card multipliers/scalers such as Triboulet-style payoff.
- Pareidolia when it unlocks multiple face-card effects.
- Strong face-card retrigger packages when face density is already meaningful.

### Silver
- Smiley Face.
- Scary Face.
- Business Card.
- Photograph.
- Sock and Buskin when sufficient face density exists.
- Baron when King density and held-card use are real.

### Bronze
- Generic scoring/economy that does not require destroying face cards.

### Preferred Tarot/Spectral support
- Rank manipulation that increases useful face density.
- Selective destruction of irrelevant low ranks.
- Copy effects targeting strong face cards.

### Conflicts
- Faceless/No-Face.
- Ride the Bus-style no-face requirements.
- Canio Destruction once destruction becomes the dominant plan.

---

## Faceless / No-Face

**Identity:** remove or avoid face cards and exploit effects that benefit from their absence, non-use, or destruction.

### Gold
- Ride the Bus when the deck can reliably avoid scoring face cards.
- Faceless Joker when discard structure supports it.

### Silver
- Low-rank payoff engines.
- Destruction tools that remove face cards while improving deck consistency.
- Rank-specific engines naturally concentrated below face ranks.

### Bronze
- Generic scoring/economy compatible with low-rank play.

### Preferred Tarot/Spectral support
- Hanged Man and other safe destruction applied to face cards.
- Rank manipulation away from face ranks when it also improves the active scoring shell.

### Conflicts
- Face Cards.
- Baron/King-heavy held-card packages.

---

## Glass

**Identity:** create and exploit Glass cards while managing breakage and replacement risk.

### Gold
- Glass Joker.
- Reliable Glass creation/duplication engines once meaningful Glass density exists.

### Silver
- Retriggers/multipliers that magnify Glass scoring.
- Copy effects that replenish or duplicate strong Glass targets.
- Hand shells that can repeatedly score strategically valuable Glass cards.

### Bronze
- Generic scoring/economy compatible with fragile scoring cards.

### Preferred Tarot/Spectral support
- Justice.
- Copy effects targeting strategically valuable Glass ranks/suits.
- Deck control that avoids wasting Glass cards on unnecessary plays.

### Risk rule
- Do not destroy the only reliable clear line merely to maximize Glass value.
- Existing Glass count and replacement capacity must matter to strategy evidence.

---

## Steel

**Identity:** keep Steel cards in hand and multiply held-card value.

### Gold
- Steel Joker.
- Mime.
- Baron when Steel Kings or King density make the package coherent.

### Silver
- Held-card scoring/retrigger effects.
- Hand-size support.
- Card generation that increases useful held cards.
- High Card/Pair shells that naturally leave many cards held.

### Bronze
- Generic scoring requiring few played cards.
- Economy that does not force excessive played-card commitment.

### Preferred Tarot/Spectral support
- Chariot.
- Death/copy effects targeting valuable Steel cards.
- Enhancement generation that preserves cards for held use.

### Natural compatibility
- High Card.
- Pair.
- Face Cards where King/face density is useful.

### Conflicts
- Vampire when it consumes Steel enhancements needed by the strategy.
- Five-card strategies that repeatedly force important Steel cards into scoring hands.

---

## Lucky

**Identity:** create Lucky-card density and exploit repeated Lucky triggers/scaling.

### Gold
- Lucky Cat once Lucky-card usage is real.
- Strong retrigger engines that substantially increase Lucky proc opportunities.

### Silver
- Magician.
- Copy effects targeting strong Lucky cards.
- Compatible per-card scoring/retrigger effects.

### Bronze
- Generic scoring/economy that keeps Lucky cards playable.

### Preferred Tarot/Spectral support
- Magician and card-copying effects.
- Deck shaping that increases the frequency of drawing/playing Lucky cards.

### Entry evidence
- Actual Lucky cards or a real repeatable Lucky-creation path.
- Theoretical future Magician access alone is not sufficient evidence.

### Conflicts
- Vampire when it is expected to consume Lucky enhancements the strategy needs to preserve.

---

## Future mechanic playbooks

Additional mechanic-specific strategies should be added here when they represent a coherent run direction rather than a one-off synergy.

Candidates may include:

- Stone-card concentration;
- Gold-card/economy shells;
- enhancement-specific retrigger shells;
- seal-specific strategies when enough dedicated support exists;
- edition-driven strategy packages when they produce coherent acquisition/play behavior.

Do not create a new playbook merely because one Joker references a mechanic. A playbook should change multiple downstream decisions: acquisition, deck shaping, consumable value, hand preservation, or scoring behavior.
