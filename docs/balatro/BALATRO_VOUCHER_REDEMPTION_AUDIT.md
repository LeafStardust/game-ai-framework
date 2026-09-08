# Balatro Voucher Redemption Audit

Pinned source: `GladdonT/balatro-source-code@895ab3a25bc6f513fa80885eb59951bf8e76bc55`.

Purpose: classify all 32 vanilla Voucher redemption consequences before broadening headless `BUY_VOUCHER` legality. This document is mechanics ownership, not strategy ranking.

## Ownership rule

A Voucher is training-buyable only when every immediate and persistent run consequence is represented exactly in canonical `BalatroState` / `HeadlessRunState` and every downstream consumer uses that state. Mere generation/publication of a Voucher card is not sufficient.

`Card:redeem()` records the Voucher in `G.GAME.used_vouchers`, removes/pays for the shop card through the ordinary shop path, then `Card:apply_to_run()` performs the Voucher-specific effect. Dependency/unlock eligibility remains owned by the authoritative observed Voucher generation catalogue.

## Complete classification

| Voucher | Source effect / persistent consumer | Ownership category | Current redemption status |
| --- | --- | --- | --- |
| Overstock | `change_shop_size(1)` | main-shop capacity / future generation | BLOCKED until mutable shop-size state replaces fixed two-slot boundary |
| Overstock Plus | `change_shop_size(1)` | main-shop capacity / future generation | BLOCKED |
| Clearance Sale | `discount_percent = 25`, then reprice all cards | pricing + immediate repricing of every current card | BLOCKED until exact current-card repricing composition is centralized |
| Liquidation | `discount_percent = 50`, then reprice all cards | pricing + immediate repricing | BLOCKED |
| Hone | `edition_rate = 2` | future Joker edition generation | BLOCKED until authoritative mutable edition-rate owner is redemption-writable end-to-end |
| Glow Up | `edition_rate = 4` | future Joker edition generation | BLOCKED |
| Reroll Surplus | subtract 2 from reset and current reroll cost | current + next-shop reroll economy | BLOCKED until both canonical reroll-cost fields are one exact owner |
| Reroll Glut | subtract 2 again | current + next-shop reroll economy | BLOCKED |
| Crystal Ball | consumable card limit `+1` | consumable capacity | EXACT-CANDIDATE: `BalatroState.consumable_slots` already authoritative |
| Omen Globe | no immediate mutation beyond used-Voucher ownership; Arcana packs consume ownership to allow Spectral generation | pack generation / RNG | BLOCKED until Arcana pack generation owns this branch |
| Telescope | no immediate mutation beyond ownership; Celestial packs force first Planet toward most-played hand | pack generation / RNG | BLOCKED until Celestial pack generation owns this branch |
| Observatory | no immediate mutation beyond ownership; held Planet cards contribute xMult during scoring | scoring + held consumable identity | BLOCKED until validated scoring bridge owns held-Planet Voucher effect |
| Grabber | `round_resets.hands += 1`; current hands `+1` | current + next-round hand allowance | EXACT-CANDIDATE when reset hands are authoritative |
| Nacho Tong | same `+1` hand effect | current + next-round hand allowance | EXACT-CANDIDATE when reset hands are authoritative |
| Wasteful | `round_resets.discards += 1`; current discards `+1` | current + next-round discard allowance | EXACT-CANDIDATE when reset discards are authoritative |
| Recyclomancy | same `+1` discard effect | current + next-round discard allowance | EXACT-CANDIDATE when reset discards are authoritative |
| Tarot Merchant | `tarot_rate = 4 * (9.6/4) = 9.6` | future main-shop type RNG | BLOCKED until mutable type-rate owner is redemption-writable |
| Tarot Tycoon | `tarot_rate = 4 * (32/4) = 32` | future main-shop type RNG | BLOCKED |
| Planet Merchant | `planet_rate = 9.6` | future main-shop type RNG | BLOCKED |
| Planet Tycoon | `planet_rate = 32` | future main-shop type RNG | BLOCKED |
| Seed Money | `interest_cap = 50` cents-equivalent source field ($10 interest cap) | round cashout economy | BLOCKED until interest-cap state is canonical and consumed by cashout |
| Money Tree | `interest_cap = 100` ($20 interest cap) | round cashout economy | BLOCKED |
| Blank | no run-mechanics mutation in `apply_to_run`; redemption advances unlock/meta progression and ownership dependency | ownership/meta unlock | BLOCKED for now; do not special-case meta side effects away merely to unlock Antimatter |
| Antimatter | Joker card limit `+1` | Joker capacity | EXACT-CANDIDATE: `BalatroState.joker_slots` already authoritative |
| Magic Trick | `playing_card_rate = 4` | future main-shop playing-card generation | BLOCKED until playing-card shop generation is owned |
| Illusion | same playing-card rate plus ownership enables enhanced/edition/seal playing-card generation branches | future card generation / RNG | BLOCKED |
| Hieroglyph | Ante `-1`; retained `blind_ante -1`; reset/current hands `-1` | Ante/blind progression + hand resource | BLOCKED until all linked progression fields are represented together |
| Petroglyph | Ante `-1`; retained `blind_ante -1`; reset/current discards `-1` | Ante/blind progression + discard resource | BLOCKED |
| Director's Cut | ownership enables one $10 Boss reroll per Ante via `boss_rerolled` state | blind generation / economy / action vocabulary | BLOCKED until strategic Boss-reroll action is owned |
| Retcon | ownership enables repeatable $10 Boss rerolls | blind generation / economy / action vocabulary | BLOCKED |
| Paint Brush | hand card-area size `+1` | hand size | EXACT-CANDIDATE: `BalatroState.hand_size` already authoritative |
| Palette | hand card-area size `+1` | hand size | EXACT-CANDIDATE |

## First exact redemption group

The smallest coherent group whose gameplay consequences are already represented is:

```text
v_crystal_ball   Crystal Ball       consumable_slots += 1
v_grabber        Grabber            round_reset_hands += 1; hands_remaining += 1
v_nacho_tong     Nacho Tong         round_reset_hands += 1; hands_remaining += 1
v_wasteful       Wasteful           round_reset_discards += 1; discards_remaining += 1
v_recyclomancy   Recyclomancy       round_reset_discards += 1; discards_remaining += 1
v_antimatter     Antimatter         joker_slots += 1
v_paint_brush    Paint Brush        hand_size += 1
v_palette        Palette            hand_size += 1
```

Fail-closed gates required for this group:

- active `SHOP` and occupied canonical `shop_vouchers` slot;
- exact generated Voucher metadata (`center_key`, exact integer `price`);
- affordability;
- no duplicate ownership of the same Voucher;
- Grabber/Nacho Tong require authoritative `round_reset_hands_observed`;
- Wasteful/Recyclomancy require authoritative `round_reset_discards_observed`;
- unsupported Voucher centers remain absent from `legal_actions()` and rejected by direct execution;
- source state remains isolated on success and rejection;
- purchase removes the Voucher from the separate `shop_vouchers` slot and records its canonical center key in `state.vouchers`.

## Explicit non-shortcuts

- Do not treat `state.vouchers.append(key)` as sufficient redemption for blocked Vouchers.
- Do not infer Voucher effects from localized description text.
- Do not use generation eligibility as proof of redemption exactness.
- Do not expose `BUY_VOUCHER` for a center merely because its shop metadata and price are exact.
- Do not silently ignore unlock/profile effects to justify Blank unless the modeled run contract explicitly decides those effects are out-of-scope and dependency behavior remains exact.
