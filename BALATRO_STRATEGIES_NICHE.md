# Balatro Strategy Catalogue — Niche Synergies

> Concrete universal niche/synergy strategy definitions.
>
> The grouping is documentation-only. At runtime every strategy is a peer in the same universal strategy pool. See [`BALATRO_STRATEGY_PLAYBOOKS.md`](BALATRO_STRATEGY_PLAYBOOKS.md) for architecture, current-state scoring, Ante pressure, and implementation rules.

## Catalogue rule

The Joker tier columns are **explicit implementation data**.

- Every Joker entry is a specific Joker name.
- **Unlisted Joker = Neutral** for that strategy.
- Bronze is an explicit weak/conditional synergy tier, not a catch-all for generic value.
- Gold/Silver/Bronze/Banned are **strategy-evidence relationships**. Owned mapped Jokers modify the current strategy score; candidates use those mappings only through the current strategy ranking and Ante-scaled strategy pressure.
- `Banned / conflict Jokers` contribute negative evidence once present and lower retention/purchase value when the niche strategy is important. They are not unconditional immediate-sell commands.
- Selling a mapped Joker removes its contribution on the next current-state recomputation.
- Generic survival/economy/meta value stays in the ordinary evaluator outside the playbook.
- Held/unopened Tarot/Spectral cards are potential future support, not achieved current strategy evidence. Their resulting persistent state matters after use.

| Strategy | Gold Jokers | Silver Jokers | Bronze Jokers | Banned / conflict Jokers | Key Tarot / Spectral support | Entry evidence |
|---|---|---|---|---|---|---|
| **Aces** | Scholar; DNA | Fibonacci; Odd Todd; Superposition; The Idol (after Ace concentration) | Hologram (when DNA is actively adding copied Aces) | Even Steven; Walkie Talkie; Hack; Wee Joker; Baron; Shoot the Moon; Hit the Road | Death; Strength; Cryptid; Grim | Multiple useful Aces plus Scholar/DNA, or a credible Ace-copy/concentration route |
| **Smeared / Splash + Flower Pot** | Flower Pot; Smeared Joker; Splash | Seeing Double; Ancient Joker; Arrowhead; Bloodstone; Onyx Agate; Rough Gem | Greedy Joker; Lusty Joker; Wrathful Joker; Gluttonous Joker | The Tribe; Droll Joker; Crafty Joker | The Lovers; The Star; The Moon; The Sun; The World; Sigil; Death | At least two package components, or Flower Pot plus deck structure already able to satisfy all effective suits reliably |
| **Canio Destruction** | Canio; Pareidolia; Trading Card | Sixth Sense (with Pareidolia); Glass Joker (face-Glass destruction shell); Oops! All 6s (only with Glass destruction shell) | Faceless Joker | Triboulet; Sock and Buskin; Photograph; Scary Face; Smiley Face; Business Card; Baron; Shoot the Moon; Hit the Road; Reserved Parking; Ride the Bus (with Pareidolia) | The Hanged Man; Immolate; Familiar; Grim; Incantation; Death | **Canio owned** is the primary activation signal; Pareidolia and repeatable face-card destruction sharply raise evidence |
| **Vampire** | Vampire; Midas Mask; Pareidolia (Midas feed shell) | Cartomancer; Vagabond; Hallucination; DNA; Marble Joker | Fortune Teller | Steel Joker; Glass Joker; Lucky Cat; Stone Joker; Golden Ticket; Driver's License | The Magician; The Empress; The Hierophant; The Lovers; The Chariot; Justice; The Devil; The Tower; Familiar; Grim; Incantation | **Vampire owned** plus existing/repeatable enhancement supply; Midas Mask/Pareidolia or reliable Tarot/Spectral generation materially raises evidence |

## Niche-strategy rules

### Package dependence

Niche strategies frequently require a **combination** rather than one globally strong item. Strategy scoring must therefore distinguish:

- a defining component that can legitimately seed the strategy;
- a package component that is weak in isolation;
- a completed or nearly completed synergy package.

For example, Flower Pot alone should not cause the agent to spend heavily chasing Smeared Joker/Splash from nothing late in a run, but Flower Pot + Smeared Joker should sharply increase that strategy's current score and therefore increase the strategy purchase value of Splash and compatible support.

### Named-engine activation

Some strategies should not become serious candidates until their defining engine exists:

- Canio Destruction requires Canio;
- Vampire requires Vampire;
- future named-engine strategies should follow the same rule when the payoff depends on one specific Joker.

Tarot/Spectral cards may still be useful before the engine exists for other strategies, but merely holding them must not falsely create Canio/Vampire strategy evidence. Their used effects may create relevant persistent state after activation.

### Conflict behavior

A banned/conflicting Joker lowers the niche strategy's current coherence rather than forcing an unconditional instant sale. If the niche strategy remains dominant/relevant despite that conflict, the conflicting Joker should receive increasing replacement pressure as Ante strategy pressure rises.

Direct functional contradictions may justify stronger urgency. For example, a Pareidolia-backed plan and Ride the Bus are functionally incompatible because Pareidolia makes every card count as a face card.

### Future niche playbooks

Additional niche playbooks can be added when a specific package changes multiple downstream decisions: Joker acquisition, Tarot/Spectral targeting, deck shaping, sell/replace behavior, or hand play.

Do not create a playbook for every two-Joker interaction. The package must be coherent enough to guide a meaningful portion of the run.
