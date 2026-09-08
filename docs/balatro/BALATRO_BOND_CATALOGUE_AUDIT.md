# Balatro Bond Catalogue Architecture Audit

This document records the Phase 6F architecture decision for the frozen 46-Bond catalogue after the minimal strategy proof passed.

The question here is **architectural admission**, not numerical calibration. A Bond is retained only when it represents a persistent, developable strategic axis whose development can change acquisition, deck shaping, preservation, or execution. Support-only state belongs in contributions/roles; exact super-additive packages belong in motifs.

## Classification vocabulary

- `KEEP` — valid independent Bond axis under the current architecture.
- `MERGE/CONTRIBUTOR` — useful mechanic, but should feed another Bond rather than own rank/realization.
- `ROLE-ONLY` — semantic role/feature only; should not own Bond development.
- `MOTIF-ONLY` — exact package belongs above Bonds as a motif.
- `REMOVE/REWORK` — current representation is not an acceptable Bond without redesign.

## Decision summary

**All 46 frozen IDs remain architecturally admissible as Bonds.**

This is not a blanket endorsement of current thresholds, contributor weights, realization functions, or role descriptors. It means the previous catalogue work has already separated the main false-Bond cases by using defining-payoff unlocks and persistent structural evidence. No Bond should be deleted or merged merely to reduce the count.

Important examples:

- `card_destruction` and `deck_thinning` remain separate: one is a current destruction engine/payoff axis; the other is the persistent deck-shape result. Their synergy was validated in Proof 2.
- `enhanced_cards` remains only because it is a **Driver's License-defined payoff axis**. Generic enhancement density alone must not create it.
- `blind_skip`, `sell_value`, `joker_sacrifice`, `hand_repetition`, `no_face_cards`, `vampire`, and `burnt` remain because each has a defining payoff/engine prerequisite. History/support without that surviving payoff must not keep the Bond alive.
- rank, suit, and poker-hand Bonds remain independent because persistent deck concentration and/or permanent hand levels can be deliberately developed and change future construction/execution.
- exact packages such as Baron-Mime-Steel and PhotoChad remain motifs/compositions, not Bonds.

## Per-Bond disposition

| Bond | Decision | Architectural basis / constraint |
|---|---|---|
| `burnt` | KEEP | Defining Joker unlock; persistent target-hand development; proven D1/run-level causal effect. |
| `held_cards` | KEEP | Multiple held-payoff sources plus persistent Steel/hand-size infrastructure; preservation authority proven at PINNED+. |
| `held_retrigger` | KEEP | Mime/copy/Red-Seal infrastructure forms an independently developable retrigger axis. |
| `steel` | KEEP | Steel density + Steel Joker + Red-Seal overlap; independent held XMult/deck-shaping axis. |
| `pair` | KEEP | Joker payoffs + permanent Pair level; directly developable hand specialization. |
| `high_card` | KEEP | Joker payoffs + permanent High Card level; directly developable hand specialization. |
| `aces` | KEEP | Ace payoffs + persistent rank density + copy bridge. |
| `no_discard` | KEEP | Multiple zero-discard payoffs/resources; explicit conflict with discard/Burnt behavior. |
| `cash` | KEEP | Bankroll/scoring/economy payoffs form a persistent resource engine distinct from Gold-card economy. |
| `lucky` | KEEP | Lucky density + Lucky-specific payoffs/probability support. |
| `glass` | KEEP | Glass density + Glass Joker destruction history; distinct high-risk scoring/scaler axis. |
| `face_cards` | KEEP | Broad face-card payoff/density axis distinct from individual King/Queen/Jack specialization. |
| `two_pair` | KEEP | Multiple Two-Pair payoffs + permanent hand level. |
| `three_kind` | KEEP | Three-of-a-Kind payoffs + permanent hand level/rank concentration. |
| `four_kind` | KEEP | Four-of-a-Kind payoff + permanent hand level/deep concentration. |
| `straight` | KEEP | Straight payoffs + structural enablers + permanent hand level. |
| `flush` | KEEP | Flush payoffs + suit concentration + permanent hand level. |
| `played_retrigger` | KEEP | Sock/Hack/Chad/Dusk + Red-Seal infrastructure create a persistent played-card retrigger axis. |
| `stone` | KEEP | Stone Joker/Marble + persistent Stone density form an independent deck/scoring axis. |
| `gold_economy` | KEEP | Gold-card density and Gold-specific generators/payoffs create an economy engine distinct from raw cash. |
| `deck_thinning` | KEEP | Persistent reduced deck size + thinning payoffs; Proof 2 validated downstream strategy value. |
| `deck_growth` | KEEP | Persistent additions + DNA/Certificate/Hologram/Marble create a distinct growth/quality axis. |
| `full_house` | KEEP | Independent permanent hand level plus Pair/Trips structure; legitimate hand-specialization track. |
| `straight_flush` | KEEP | Independent permanent hand level and persistent straight+suit construction requirements. |
| `five_kind` | KEEP | Independent permanent hand level + extreme rank concentration/copy support. |
| `flush_house` | KEEP | Independent permanent hand level + persistent suited Full-House construction. |
| `flush_five` | KEEP | Independent permanent hand level + same-rank/same-suit concentration/copy support. |
| `hearts` | KEEP | Hearts payoffs + persistent suit density; suit specialization axis. Density-only evidence must remain low-authority infrastructure. |
| `spades` | KEEP | Spade payoffs + persistent suit density; same density-only constraint. |
| `clubs` | KEEP | Club payoffs + persistent suit density; same density-only constraint. |
| `diamonds` | KEEP | Diamond payoffs + persistent suit density; same density-only constraint. |
| `low_ranks` | KEEP | Hack/Wee/Fibonacci/etc. + persistent 2–5 density form a reusable rank-family axis. |
| `kings` | KEEP | Baron/Triboulet + King density; independent rank specialization and held-engine bridge. |
| `queens` | KEEP | Shoot the Moon/Triboulet + Queen density; independent rank specialization. |
| `jacks` | KEEP | Hit the Road + Jack density; defining rank payoff and shaping axis. |
| `tarot` | KEEP | Persistent Tarot generation/access infrastructure affects deck-shaping resource strategy. Must not be treated as direct scoring power. |
| `planet` | KEEP | Persistent Planet generation/access + Blue Seals support hand-level strategy. Must remain subordinate to selected hand relevance. |
| `discard` | KEEP | Hard-unlocked by real discard payoffs; extra discard capacity/history is support only. Explicitly conflicts with No-Discard and synergizes with Burnt. |
| `blind_skip` | KEEP | Throwback hard unlock makes skip history strategically persistent; tags/history alone cannot create the Bond. |
| `sell_value` | KEEP | Swashbuckler hard unlock converts sell value into a real scoring axis; Egg/Gift Card alone remain economy components. |
| `joker_sacrifice` | KEEP | Dagger/Madness hard unlock; sacrifice history/fodder support only while a surviving payoff exists. |
| `card_destruction` | KEEP | Current destruction engine/payoff required; history without engine falls back to persistent deck-thinning state. |
| `hand_repetition` | KEEP | Card Sharp/Supernova hard unlock gives repeated-hand history independent strategic meaning. |
| `enhanced_cards` | KEEP | Valid only as Driver's License-defined enhancement-density payoff axis; generic enhancement state alone is not a Bond. |
| `no_face_cards` | KEEP | Ride the Bus hard unlock + persistent face depletion; explicit conflict with Face Cards. |
| `vampire` | KEEP | Vampire hard unlock + enhancement feed/consumption history; explicit conflict with preserve-enhancement strategy. |

## Why no merge/removal is justified yet

The minimal proof established that the architecture can distinguish:

1. development from commitment;
2. FORMING construction authority from PINNED preservation authority;
3. aligned engine reinforcement from unrelated rank collection;
4. explicit conflict from genuine strategy reinforcement.

Given those controls, overlapping Bonds are not automatically double-counting. One component may legitimately contribute to multiple independent strategy tracks. The correct next question is therefore **whether each retained Bond's contributors, roles, realization, and rank thresholds are mechanically valid and reachable**, not whether the catalogue count should be reduced for its own sake.

## Watchlist for the next audit pass

These retained Bonds deserve focused validation before any numerical tuning:

- **Suit Bonds (`hearts`, `spades`, `clubs`, `diamonds`)** — verify natural/density-only R0 evidence cannot independently form an authoritative strategy without payoff semantics.
- **Rare hand Bonds (`straight_flush`, `five_kind`, `flush_house`, `flush_five`)** — verify permanent hand-level/concentration evidence is reachable and does not create premature commitment from theoretical structure alone.
- **Resource Bonds (`tarot`, `planet`)** — verify they remain infrastructure/strategy resources and never become imaginary direct score.
- **Broad payoff Bonds (`cash`, `face_cards`, `enhanced_cards`)** — verify overlapping contributors do not create duplicate structural reward without a real semantic transition.
- **Hard-unlock Bonds** — verify history/state disappears as strategic authority when the defining payoff Joker is sold/destroyed.

## Phase 6F decision

Catalogue **architecture** is retained. Phase 6F should continue with a mechanical validity/reachability audit of the retained Bonds before any threshold tuning or live Tune G.

Order of work:

1. validate contributor correctness and hard-unlock semantics;
2. validate role/target/condition descriptors used by strategy formation;
3. validate realization against literal mechanics;
4. measure realistic R1–R5 reachability from the actual contributor economy;
5. only then calibrate thresholds/weights where evidence demonstrates a defect;
6. after catalogue semantics are green, return to controlled live validation/tuning.
