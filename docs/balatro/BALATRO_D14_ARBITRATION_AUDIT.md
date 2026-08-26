# Balatro D14 Cross-Family Arbitration Audit

Status: **Static arbitration semantics implemented; current-HEAD local validation and later tuning pending**

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

### Generic visible two-Joker Bond planning

Ordinary D2 evaluates one visible Joker against the current roster. That leaves one bounded blind spot: two simultaneously visible Jokers may become a valid composition only together even though neither clears the standalone D2 purchase threshold before the other is owned.

`bond_visible_shop_bundle_policy.py` closes that gap through the canonical Bond/composition system rather than a named-pair table:

- neither component may already be an actionable standalone D2 purchase;
- the first component must already be a mechanically eligible D2 ADD option and may fail only standalone purchase advantage;
- the exact first purchase is projected with its real cash/slot transition;
- canonical D2 is rerun on the second visible Joker in that projected state;
- the second must become an actual D2 `BUY`, and its modeled build gain must strictly improve after adding the first component, proving a composition interaction rather than two unrelated speculative purchases;
- both steps are normalized sequentially through the existing D14 `ShopUtilityScale`;
- the combined verified gain must beat the action ordinary D14 would otherwise execute.

Only the first purchase is emitted. The agent then re-observes the settled shop and requires a fresh D2 `BUY` for the still-visible second component before completing the pair. A disappeared, unaffordable or no-longer-admitted second Joker cancels the commitment. No hidden future shop contents, RNG state or named Joker combination is used.

The historical `short_horizon_shop_planner.py` remains in the repository for historical/offline compatibility, but its `BUILD_HEALTH_BUNDLE` production checkpoint is explicitly retired when the canonical Bond bundle policy installs. Build Health continues to provide its other health/reroll behavior; it can no longer inject hard-coded combinations such as Bull+Bootstraps, Baron+Mime, Photograph+Hanging Chad, or hand-type pairs into live D14. The Bond-derived planner is the sole production authority for visible multi-Joker combination assembly.

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

## Voucher authority — implementation repaired with grounded/fail-closed horizons

D3 is authoritative for ordinary voucher BUY/HOLD admission. D14 recomputes voucher purchase resource cost on the shared parent scale. D3 strategic admission does not entitle a persistent voucher to an arbitrary fixed D14 cross-family number.

The following vouchers have grounded parent behavior:

- **Antimatter** — marginal public future-Joker option from `joker_slots -> joker_slots + 1`, evaluated at post-purchase cash through the same D11/D2/D14 Joker expectation used by Ectoplasm;
- **Paint Brush / Palette** — literal expected best-play improvement from `hand_size -> hand_size + 1` using the same public draw and D2 direct-score scale used by Ouija/Ectoplasm hand-size opportunity cost;
- **Grabber / Nacho Tong** — exact `+1 hand` value propagated only across Boss Blind rounds that are unavoidably required to win through the configured Ante-8 target. Small and Big Blinds are omitted because playing rather than skipping them is a future policy choice. Only the shared resource model's invariant direct hand component is propagated; current-blind survival pressure is not copied onto unseen bosses;
- **Wasteful / Recyclomancy** — the same unavoidable Boss-round lower bound for `+1 discard`. Existing D3 conflict/mechanical vetoes such as Burglar remain authoritative;
- **Observatory** — literal current-build score change from adding the voucher to the current state, using the installed exact `1.5 ** matching_held_planets` scoring effect. Future Planet acquisition and Perkeo infrastructure are deliberately omitted instead of receiving a synthetic premium;
- **Seed Money / Money Tree** — conservative improvement to the next interest payout at actual post-purchase cash. Later-round compounding is omitted rather than assigned a synthetic horizon premium;
- **Blank** — special collection/progression authority while Antimatter remains observably locked. Balatro's public `v_antimatter.unlocked` center flag is exposed directly. D3 may admit Blank only when ordinary affordability and survival/reserve gates pass. D14 lets that unlock progression cover Blank's direct sticker-price term plus a bounded tie-break, while lost interest, reserve pressure and Bull/Bootstraps cash-scaling opportunity cost remain fully charged. Once Antimatter is unlocked, Blank's progression parent value becomes zero.

Blank's progression exception is intentionally separate from ordinary gameplay utility: the redemption is a real step toward the ten-Blank Antimatter unlock, but it must not force a purchase that damages the current Red/White run.

### Policy-contingent persistent vouchers fail closed

The remaining persistent voucher families require a future *choice*, not an unavoidable event. D14 therefore assigns them `0.0` current parent gain instead of inheriting a legacy fixed D3 value or inventing an assumed count:

- **Telescope** — requires choosing a future Celestial pack;
- **Clearance Sale / Liquidation** — require one or more future purchases;
- **Reroll Surplus / Reroll Glut** — require choosing one or more future rerolls;
- **Magic Trick / Illusion** — require future playing-card shop opportunities;
- **Hieroglyph / Petroglyph** — require a common-unit treatment of the immediate Ante decrease versus their permanent hand/discard resource loss.

This is deliberate fail-closed arbitration, not missing Balatro mechanics. D3 may still admit these vouchers strategically. D14 simply refuses to compare an invented future-policy payoff against literal Joker/consumable/booster utility until a grounded planning horizon/common unit exists.

## Tuning boundary

Threshold-driven shop guards such as early cash floors, late-shop reserve thresholds and D13 tag-vs-development preferences remain calibration work. They should be tuned from local/live evidence after semantic correctness is validated rather than rewritten here as new mechanics.

## Hidden-information guarantee

None of the repaired D14 paths read:

- Balatro RNG state or pseudoseeds;
- future shop order;
- hidden booster contents;
- ordered future draw pile.

Random future effects are integrated over public eligible catalogues or public deck composition, with deterministic bounded sampling only where exact combinatorial enumeration is too large. Antimatter progression uses only the loaded public center unlock flag.

## Validation status

No tests were run by the assistant. Current-HEAD deterministic and live validation remain the user's local gate. Semantic D14 arbitration no longer has a synthetic persistent-voucher blocker; threshold calibration and any contradictions reproduced by local/live validation remain follow-up work.
