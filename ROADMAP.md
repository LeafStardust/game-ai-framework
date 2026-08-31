# ROADMAP — SINGLE SOURCE OF TRUTH

This file is written for an LLM continuing development of this repository.

**This is the only authoritative roadmap, handoff, queue, or current-status document in the repository.**

Rules:

1. Read this file first.
2. Treat `CURRENT STATE` and `EXACT NEXT ACTION` as authoritative.
3. Other `docs/` files are supporting evidence/history only.
4. If local test evidence proves this stale, update it in the same batch.
5. Do not create another roadmap/handoff file.

---

# REPOSITORY CONTRACT

- Repository: `LeafStardust/game-ai-framework`
- Active branch: `feat/v1.0-red-white-competence`
- User runs tests locally. **Do not run tests from ChatGPT.**
- Every local validation command must begin with `git pull`.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order, future identities, or inaccessible information.
- Prefer canonical ownership over late monkeypatch/rescue wrappers.
- Do not use broad tuning to compensate for semantic defects.

---

# ACTIVE GAMEPLAY OBJECTIVE

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

---

# CURRENT STATE — 2026-08-31

Active phase:

> **Phase 2 — simple shop survival. Batch 1 implemented, validation pending.**

Phase 0 authority consolidation: **COMPLETE / VALIDATED**.

Phase 1 D1 survival semantic expansion: **COMPLETE / VALIDATED**.

Canonical owners:

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`

Canonical authority shape:

```text
Authoritative public state
        ↓
Literal Balatro mechanics
        ↓
Legal candidates
        ↓
Bounded projection
        ↓
One run-winning evaluator
        ↓
One final arbiter
        ↓
Action
```

---

# VALIDATED BASELINE

Full deterministic Balatro suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Result: **GREEN**.

Phase-0 semantic exit benchmark: **24/24 GREEN**.

Phase-1 final semantic benchmark: **33/33 GREEN**:

- `BUILD_COHERENCE`: 2/2
- `D1_SURVIVAL`: 22/22
- `SHOP_SURVIVAL`: 9/9

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and reflects current native authority.

---

# PHASE 1 — CLOSED

Phase 1 was intentionally capped at five batches and is now complete. No Batch 6 is queued absent fresh evidence.

Validated additions:

1. guaranteed clear preserves discard resource;
2. recursive Cerulean candidates preserve boss legality;
3. under-pace play yields to materially stronger redraw;
4. final discard is conserved for only marginal recovery;
5. timeout reuses latest completed canonical root;
6. timeout does not promote unconfirmed sampled clears;
7. last-hand recovery preserves the final scoring opportunity;
8. public redraw value is invariant to hidden serialized deck order;
9. deterministic held-consumable clear projection executes only `USE_CONSUMABLE`, then re-observes/replans.

Do not expand Phase 1 merely to increase semantic case count.

---

# PHASE 2 — SIMPLE SHOP SURVIVAL

Goal: protect basic Red/White shop decisions before deeper composition/build optimization.

Audit order:

1. explicit END_SHOP/no-action survival baseline;
2. free versus paid reroll behavior;
3. transaction checkpoint safety for replacement/sell/buy flows;
4. early scoring foothold versus support/economy spending;
5. cash/reserve stop-loss on ordinary purchases and paid rerolls;
6. only then compare cross-family simple purchases.

Existing SHOP semantics already protect first scoring foothold, strategic conflict vetoes, first-engine-before-hand-size, Wheel admission, empty-roster Buffoon admission, visible Bond-pair authority, and pair interaction requirements.

## Batch 1 — IMPLEMENTED / VALIDATION PENDING

Commits:

- `f2de18be` — adds `red_white_semantic_phase2_shop_cases.py`.
- `7a1a8188` — wires Phase-2 cases into `red_white_semantic_benchmark`.

New cases:

1. `shop.simple.end_shop_zero_baseline`
   - an admitted family-local child with negative normalized parent value must lose to explicit `END_SHOP`;
   - owner if it fails: `BuildAwareShopArbiter` parent candidate arbitration.
2. `shop.simple.free_reroll_zero_tie`
   - a genuinely free reroll beats `END_SHOP` on an otherwise exact zero-gain tie;
   - owner if it fails: D14 reroll tie priority / D11-D14 handoff.
3. `shop.simple.replacement_reobserve_boundary`
   - a profitable Joker replacement executes only `SELL_JOKER`, then requires fresh authoritative SHOP observation before any follow-up `BUY_JOKER`;
   - owner if it fails: `BuildAwareShopArbiter` replacement transaction boundary.

No production code or tuning values changed in Batch 1.

Expected benchmark if all three pass: **36/36**, with `SHOP_SURVIVAL` increasing from 9/9 to 12/12.

---

# EXACT NEXT ACTION

Validate Phase-2 Batch 1 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 36/36 green

Continue Phase 2 with the next coherent simple-shop survival batch, prioritizing paid-reroll stop-loss and ordinary cash/reserve spending boundaries. Do not tune values unless a semantic case exposes a real defect.

### If a new case fails

Determine fixture defect versus production semantic defect. Fix the smallest canonical owner. Do not add wrapper rescues.

---

# PHASE ORDER

1. **Phase 0 — authority consolidation** — COMPLETE
2. **Phase 1 — D1 survival semantic expansion** — COMPLETE
3. **Phase 2 — simple shop survival** — ACTIVE
4. **Phase 3 — coherent build evidence/authority quality**
5. **Phase 4 — complex packs/consumables/vouchers/economy audit**
6. **Phase 5 — live validation**
7. **Phase 6 — numerical tuning only after semantics are trustworthy**

Future stake/deck progression remains blocked until Red/White competence passes.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- Phase-0 D1 ownership migration queue
- Phase-1 semantic expansion beyond five validated batches
- Mouth discard-only legality defect itself
- Green Joker survival-equivalent authority
- Hook/log-resilience search reserve
- target-hand installer architecture
- Purple-Seal installer architecture
- held-round-end-resource installer architecture
- semantic-search-guard installer architecture
- Serpent installer architecture
- Hook planner installer architecture
- Cerulean installer architecture
- Ectoplasm installer architecture
- round-resource installer architecture
- Joker-generation live-state installer architecture
- boss-hand-constraint installer architecture
- production-default tuning ContextVar hypothesis — falsified
- historical SHOP recursive expectation roots
- BLIND_SELECT quiescence deadlock
- ROUND_EVAL checkout fast-path semantics
- D1 root pre-beam wall-clock budget defect
- live tuner cascading after failed/non-COMPLETE trial
- Phase-A Bond exploratory tuning — completed with no promotion
- D14/D11 SHOP latency blocker unless fresh timing evidence reproduces it
