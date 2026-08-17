# Balatro Strategy Catalogue — Mechanics

> Concrete universal mechanic-specific strategy definitions.
>
> The grouping is documentation-only. At runtime every strategy is a peer in the same universal strategy pool. See [`BALATRO_STRATEGY_PLAYBOOKS.md`](BALATRO_STRATEGY_PLAYBOOKS.md) for architecture and lifecycle rules.

| Strategy | Gold | Silver | Bronze | Must avoid / conflicts | Key Tarot/Spectral/support | Entry evidence |
|---|---|---|---|---|---|---|
| **Face Cards** | Major face-card multiplier/scaler such as Triboulet-style payoff; Pareidolia when it unlocks multiple face effects; strong face-card retrigger package with real face density | Smiley Face; Scary Face; Business Card; Photograph; Sock and Buskin with sufficient face density; Baron with real King/held-card support | Generic scoring/economy that preserves face cards | Faceless/No-Face; Ride the Bus-style no-face requirements; Canio Destruction once destruction is the plan | Strength/rank manipulation increasing useful face density; selective low-rank destruction; Death/copy on valuable face cards | Owned face-payoff Jokers; meaningful face density; repeated face-card scoring |
| **Faceless / No-Face** | Ride the Bus when face scoring can be reliably avoided; Faceless Joker when discard structure supports it | Low-rank payoff engines; destruction tools that remove face cards while improving consistency; matching non-face rank engines | Generic scoring/economy compatible with low-rank play | Face Cards; Baron/King-heavy shells | Hanged Man on face cards; rank manipulation away from faces when it also improves the scoring shell | No-face payoff owned; reduced face density; actual ability to avoid scoring faces |
| **Glass** | Glass Joker; reliable Glass creation/duplication engine after meaningful Glass density exists | Retriggers/multipliers magnifying Glass; copy effects replenishing strong Glass targets; compatible repeated scoring shell | Generic scoring/economy compatible with fragile cards | Wasteful Glass use; transformations that remove essential Glass cards; survival lines depending on consuming the only reliable Glass scorer | Justice; Death/copy on premium Glass cards; deck control that avoids unnecessary Glass plays | Existing Glass cards; Glass Joker; repeatable Glass creation. Theoretical future Justice alone is weak evidence |
| **Steel** | Steel Joker; Mime; Baron when Steel Kings/King density make the package coherent | Held-card scoring/retriggers; hand-size support; generation of useful held cards; High Card/Pair shells that naturally leave cards held | Generic low-card scoring; compatible economy | Vampire when it consumes needed Steel enhancements; five-card shells that repeatedly force premium Steel cards to score | Chariot; Death/copy on valuable Steel cards; hand-size/held-card support | Existing Steel cards; Steel Joker/Mime; held-card build structure |
| **Lucky** | Lucky Cat after Lucky usage exists; strong retrigger engines that materially increase Lucky proc opportunities | Magician; copy effects on strong Lucky cards; compatible per-card retriggers/scoring | Generic scoring/economy preserving Lucky cards | Vampire when it consumes Lucky enhancements needed by the strategy | Magician; Death/copy; deck shaping increasing Lucky draw/play frequency | Actual Lucky cards or a repeatable Lucky-creation path; theoretical future Magician alone is insufficient |

## Candidate future mechanic strategies

Only add one when it changes **multiple downstream decisions**, not merely because a Joker references the mechanic.

| Candidate | Why it may deserve a playbook | Do not add until |
|---|---|---|
| Stone | Card-identity-independent scoring and deck-shape changes | Enough concrete Joker/consumable interactions form a coherent acquisition and play plan |
| Gold cards | Held-card economy and enhancement preservation | It has a real run direction beyond generic economy valuation |
| Seal-specific | Blue/Purple/Red seal engines can alter hand preservation and consumable value | Dedicated support is sufficient to drive repeated decisions |
| Edition-driven | Edition generation/copying may create coherent Joker/card acquisition priorities | It affects strategy beyond simply “edition is good” |

## Mechanic-strategy rule

Tarot and Spectral cards may **seed these strategies during Antes 1–2**. Unlike Planets, the agent does not need an already dominant strategy before accepting a transformative early enhancement, destruction, rank, suit, or copying opportunity.

As the run converges, generic transformation value decreases and contribution to the dominant/relevant strategies becomes increasingly important.
