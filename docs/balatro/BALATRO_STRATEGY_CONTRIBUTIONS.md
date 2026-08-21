# Balatro Strategy Contributions

Canonical component/state -> Bond contribution values. Architecture is defined in `BALATRO_STRATEGY_SYSTEM.md`; catalogue identity/rank behavior is in `BALATRO_STRATEGY_CATALOGUE.md`.

## Rules

- Gold/Silver/Bronze/Banned is legacy migration evidence only.
- Every accepted source contributes its own numerical weight to one or more Bonds.
- All valid sources for one Bond feed one shared pool; contributors are alternative/additive routes, never sequential rank keys.
- Persistent deck/state contribution uses bands/caps where appropriate.
- `LOCKED` means a defining prerequisite is absent. `R0` means the Bond exists as a possible axis but is below R1.
- Rank is structural development. Realization and Build Health remain separate.
- Multi-Bond contribution is intentional and never becomes fake additive scoring power.

All values below are provisional Red/White calibration and must be audited again after the catalogue is complete.

---

## 1. Burnt

**Unlock:** Burnt Joker required.

**Thresholds:** `8 / 12 / 17 / 23 / 30`

| Source | Contribution |
|---|---:|
| Burnt Joker | +8 |
| Blueprint | +5 |
| Brainstorm | +5 |
| Telescope | +4 |
| Space Joker | +2 |
| Blue Seals: 1 / 2 / 3 / 4+ | +1 / +3 / +5 / +6 cap |
| Target hand level: 2-3 / 4-6 / 7-10 / 11+ | +1 / +3 / +5 / +7 cap |
| Extra discards above 3 | +1 each, +3 cap |

Excluded: Astronomer, generic Planets, Scholar/Aces infrastructure, generic scoring.

## 2. Held Cards

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Baron | +6 |
| Shoot the Moon | +4 |
| Raised Fist | +2 |
| Steel cards: 1 / 2-3 / 4-5 / 6+ | +1 / +3 / +5 / +7 cap |
| Hand size above 8 | +1 each, +3 cap |

**Explicit exclusions:** Mime, Gold Cards, Blue Seals. Mime belongs to Held Retrigger; Gold/Blue being held is a trigger condition rather than this Bond's identity.

## 3. Held Retrigger

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Mime | +6 |
| Red Seals: 1 / 2-3 / 4-5 / 6+ | +1 / +3 / +5 / +7 cap |
| Blueprint while Mime exists | +4 |
| Brainstorm while Mime exists | +4 |

Mime contributes here, not to Held Cards. Its super-additive value with Baron/Steel/etc. is represented by Bond synergy/motifs.

## 4. Steel

**Unlock:** none. **Thresholds:** `4 / 8 / 14 / 21 / 29`

| Source | Contribution |
|---|---:|
| Steel Joker | +5 |
| Steel cards: 1 / 2-3 / 4-5 / 6-9 / 10+ | +1 / +3 / +6 / +9 / +12 cap |
| Red-Seal Steel cards: 1 / 2-3 / 4+ | +1 / +2 / +3 cap |

Steel cards legitimately contribute to Steel and Held Cards simultaneously.

## 5. Pair

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| The Duo | +6 |
| Jolly Joker | +4 |
| Sly Joker | +4 |
| Half Joker | +2 |
| Pair level: 2-3 / 4-6 / 7-10 / 11+ | +1 / +3 / +5 / +7 cap |

Hand play-count history alone does not create Pair development.

## 6. High Card

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Stuntman | +6 |
| Half Joker | +3 |
| High Card level: 2-3 / 4-6 / 7-10 / 11+ | +1 / +3 / +5 / +7 cap |

Burnt may target High Card by composition/fallback, but Burnt is not itself High Card quota.

## 7. Aces

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Scholar | +6 |
| Fibonacci | +3 |
| Ace density: 4 / 6 / 8 / 12+ | +1 / +3 / +5 / +7 cap |
| DNA with at least 6 Aces | +4 |

DNA is a conditional bridge: it does not establish Aces merely by being owned.

## 8. No-Discard

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Green Joker | +6 |
| Burglar | +6 |
| Delayed Gratification | +4 |
| Ramen | +4 |
| Banner | +2 |

Explicit relationship: `Burnt x No-Discard = CONFLICT`.

## 9. Cash

**Unlock:** none. **Thresholds:** `4 / 9 / 15 / 22 / 30`

| Source | Contribution |
|---|---:|
| Bull | +5 |
| Bootstraps | +5 |
| Rocket | +4 |
| Golden Joker | +3 |
| To the Moon | +3 |
| Satellite | +3 |
| Reserved Parking | +2 |
| Bankroll: $25 / $50 / $100 / $150+ | +1 / +3 / +5 / +7 cap |

Cash rank represents developed cash infrastructure, not a command to hoard regardless of Build Health.

## 10. Lucky

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Lucky Cat | +6 |
| Oops! All 6s | +4 |
| Lucky cards: 1 / 3 / 6 / 10+ | +1 / +3 / +5 / +7 cap |

## 11. Glass

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`

| Source | Contribution |
|---|---:|
| Glass Joker | +6 |
| Glass cards: 1 / 3 / 6 / 10+ | +1 / +3 / +5 / +7 cap |
| Destroyed Glass while Glass Joker owned: 1 / 3 / 6 / 10+ | +1 / +2 / +4 / +6 cap |

The destruction term reflects persistent Glass Joker development only while the Joker remains owned.

## 12. Face Cards

**Unlock:** none. **Thresholds:** `4 / 9 / 15 / 22 / 30`

| Source | Contribution |
|---|---:|
| Pareidolia | +6 |
| Sock and Buskin | +5 |
| Photograph | +4 |
| Scary Face | +4 |
| Smiley Face | +4 |
| Business Card | +2 |
| Natural face-card density: 12 / 16 / 20 / 26+ | +1 / +3 / +5 / +7 cap |

Bosses such as The Plant affect realization/score projection, not structural Bond rank.

---

## Sparse relationships currently encoded

```text
Burnt x No-Discard             = CONFLICT
Held Cards <-> Held Retrigger  = SYNERGY
Held Cards <-> Steel           = SYNERGY
Held Retrigger <-> Steel       = SYNERGY
```

Everything else defaults to `NEUTRAL` until a mechanically meaningful edge is established. Complex packages belong to motifs rather than an exhaustive relationship matrix.
