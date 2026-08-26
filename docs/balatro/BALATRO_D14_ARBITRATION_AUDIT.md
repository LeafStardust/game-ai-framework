# Balatro D14 Cross-Family Arbitration Audit

Status: **Active implementation audit — narrowed to horizon-dependent persistent vouchers**

Date: 2026-08-26

This document records the current production authority for SHOP cross-family comparison on `feat/v1.0-red-white-competence`. It is an implementation audit, not a claim that current HEAD has passed the user's local deterministic suite or live validation.

## Parent contract

D14 compares only child options that their own decision layer already admitted. `END_SHOP` is the zero-gain parent baseline. Money, interest, reserve, cash-scaling and finite-slot opportunity costs are recomputed on the shared `ShopUtilityScale` / `RunResourceValuator` scale rather than inherited from arbitrary child coefficients.

Child admission remains separate:

- D2 — Joker acquisition/replacement;
- D3 — Voucher acquisition;
- D4 — Consumable BUY / BUY_AND_USE;
- D8 — unopened booster acquisition;
- D11 — paid/free reroll opportunity;
- D14 — cross-family comparison only.

## Joker authority — implementation repaired

Joker parent value uses:

- literal current/candidate whole-build score;
- public stochastic score expectation where required;
- actual candidate edition value;
- post-transaction cash state;
- exact replacement incumbent/candidate baseline;
- shared money/interest/reserve/cash-scaling cost;
- actual Joker-slot opportunity cost;
- exact selected shop-copy identity for committed replacement.

Sold Bull/Bootstraps do not remain in post-sale cash-scaling opportunity cost.

## Consumable authority — implementation repaired

D4 may use B4 structural/build-path units for child admission, but those units no longer enter D14 directly.

### Held Tarot / Spectral BUY

`held_consumable_option_policy.py` values the candidate by expected actual future use on representative fresh hands from the unordered public permanent deck. The fully installed D9 mechanics score each branch against opened-pack Skip=0. Unsupported/incomplete branches remain zero in the expectation rather than being renormalized away.

Generation Tarots whose held-slot timing differs from direct pack selection fail closed at D14 rather than inheriting B4 structural value.

### Planet BUY / BUY_AND_USE

`consumable_d14_literal_policy.py` compares literal representative whole-build score before/after holding or mechanically using the Planet. Planet use increments the hand level and sends active Jokers the real `PLANET_USED` trigger, so Constellation progress is represented mechanically rather than by a scaler bonus.

### Immediate BUY_AND_USE

For non-Planet immediate transactions such as Hermit/Temperance, D14 keeps only the explicit D4 immediate-money value and shared purchase resource cost. B4 structural gain is admission-only.

## Booster authority — implementation repaired

All five D8 families now use public-mechanics option expectations rather than their historical fixed family hit/value priors:

- Buffoon — eligible Joker pool through D2/D14;
- Celestial — eligible Planet pool and literal permanent hand-level/scaler projection;
- Standard — exact public rank/suit/enhancement/seal/edition generator with literal playing-card/deck-growth value;
- Arcana — public Tarot/Spectral pools, Omen Globe branch and soulable override;
- Spectral — public Spectral pool and soulable Black-Hole/Soul override.

D14 subtracts shared pack purchase resource cost once.

## Reroll authority — implementation repaired for all three vanilla shop-card families

D11 no longer relies on fixed gross value for future Joker, Planet or Tarot identity:

- Joker — current public eligible Joker rarity pools through D2/D14, with public edition odds;
- Planet — current eligible Planet pool through D4/D14;
- Tarot — current public eligible Tarot pool, each outcome valued as a future held-use option on public fresh-hand draws.

Future exact item identity is never observed. Unseen future sticker price remains the explicit D11 price prior. Reroll purchase cost is charged separately after future-shop option EV.

## Voucher authority — partially repaired

D3 is authoritative for ordinary voucher BUY/HOLD admission. D14 recomputes voucher purchase resource cost on the shared parent scale.

The following vouchers now have grounded parent behavior instead of their legacy fixed D3 number:

- **Antimatter** — marginal public future-Joker option from `joker_slots -> joker_slots + 1`, evaluated at post-purchase cash through the same D11/D2/D14 Joker expectation used by Ectoplasm;
- **Paint Brush / Palette** — literal expected best-play improvement from `hand_size -> hand_size + 1` using the same public draw and D2 direct-score scale used by Ouija/Ectoplasm hand-size opportunity cost;
- **Observatory** — literal current-build score change from adding the voucher to the current state, using the installed exact `1.5 ** matching_held_planets` scoring effect. Future Planet acquisition and Perkeo infrastructure are deliberately omitted instead of receiving a synthetic premium;
- **Seed Money / Money Tree** — conservative improvement to the next interest payout at actual post-purchase cash. Later-round compounding is omitted rather than assigned a synthetic horizon premium;
- **Blank** — special collection/progression authority while Antimatter remains observably locked. Balatro's public `v_antimatter.unlocked` center flag is exposed directly. D3 may admit Blank only when ordinary affordability and survival/reserve gates pass. D14 lets that unlock progression cover Blank's direct sticker-price term plus a bounded tie-break, while lost interest, reserve pressure and Bull/Bootstraps cash-scaling opportunity cost remain fully charged. Once Antimatter is unlocked, Blank's progression parent value becomes zero.

Blank's progression exception is intentionally separate from ordinary gameplay utility: the redemption is a real step toward the ten-Blank Antimatter unlock, but it must not force a purchase that damages the current Red/White run.

### Remaining D14 implementation blocker

Other persistent vouchers still use D3 strategic persistent values because their effect is inherently multi-round/horizon dependent and does not yet have a common parent-scale mechanical model. Examples include:

- Grabber / Nacho Tong — +1 hand per round;
- Wasteful / Recyclomancy — +1 discard per round;
- Telescope — future Celestial-pack guarantee;
- Clearance Sale / Liquidation — future shop-price reduction;
- Reroll Surplus / Reroll Glut — future reroll-price reduction;
- Hieroglyph / Petroglyph — Ante/resource tradeoffs;
- Magic Trick / Illusion — future playing-card shop pool;
- other prerequisite/progression vouchers whose unlock objective has not been explicitly modeled.

These effects should not be replaced by another universal constant merely to make the D14 checkbox green. They require either direct public-state horizon projection or an explicitly shared strategic parent unit suitable for comparison with the other families.

## Hidden-information guarantee

None of the repaired D14 paths read:

- Balatro RNG state or pseudoseeds;
- future shop order;
- hidden booster contents;
- ordered future draw pile.

Random future effects are integrated over public eligible catalogues or public deck composition, with deterministic bounded sampling only where exact combinatorial enumeration is too large. Antimatter progression uses only the loaded public center unlock flag.

## Validation status

No tests were run by the assistant. Current-HEAD deterministic and live validation remain the user's local gate. D14 should remain unchecked in the Red/White roadmap until the remaining persistent-voucher parent-value problem is addressed and the resulting HEAD is locally validated.
