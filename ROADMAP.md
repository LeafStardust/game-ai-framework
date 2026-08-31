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

> **Phase 3 — coherent build evidence/authority quality. Batch 1 implemented, validation pending.**

Phase 0 authority consolidation: **COMPLETE / VALIDATED**.

Phase 1 D1 survival semantic expansion: **COMPLETE / VALIDATED**.

Phase 2 simple shop survival: **COMPLETE / VALIDATED**.

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

Phase-2 final semantic benchmark: **42/42 GREEN**:

- `BUILD_COHERENCE`: 2/2
- `D1_SURVIVAL`: 22/22
- `SHOP_SURVIVAL`: 18/18

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and reflects current native authority.

---

# PHASE 1 — CLOSED

Phase 1 was intentionally capped at five batches and is complete. No Batch 6 is queued absent fresh evidence.

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

# PHASE 2 — CLOSED

Phase 2 was capped at four batches and is complete at **42/42**.

Validated simple-shop survival coverage:

1. explicit zero-gain `END_SHOP` baseline;
2. free-reroll tie behavior;
3. replacement sell/re-observation transaction boundary;
4. paid-reroll absolute cost stop-loss;
5. paid-reroll cash-reserve stop-loss;
6. bounded first-engine reserve relaxation;
7. ordinary Joker reserve-crossing economics;
8. shared-scale first-engine versus support/economy ordering in both directions.

Important Batch-3 fixture history:

- the runtime D2 stack includes installed post-transaction Joker revaluation through `transition_planner.evaluator.evaluate()`;
- semantic fixtures must model that path when controlling synthetic Joker build gain;
- no production behavior was changed by the Batch-3 fixture repairs.

Do not add a Phase-2 Batch 5 merely to increase semantic coverage count.

---

# PHASE 3 — COHERENT BUILD EVIDENCE / AUTHORITY QUALITY

Goal: ensure D2/D14 build evidence distinguishes real scoring, support, scaling, economy, and composition without creating duplicate scoring authority or converting structural evidence into fake immediate power.

Audit order:

1. scoring-engine versus support/economy role separation;
2. scaling evidence versus already-realized scoring power;
3. contextual interaction value versus standalone intrinsic value;
4. Bond/composition evidence must not duplicate literal score arithmetic;
5. replacement/pivot evidence must remain downstream of legal D2 economics;
6. only after these semantics are clean, consider any numerical weighting questions.

Build Health, Bond rank, motifs, and composition remain evidence/planning layers. They do not replace D1 survival authority or D14's final SHOP arbitration.

## Batch 1 — IMPLEMENTED / VALIDATION PENDING

Commits:

- `0f5b0f3a` — adds `red_white_semantic_phase3_build_cases.py`.
- `a89e8e6e` — wires Phase-3 build cases into the semantic benchmark.

New cases:

1. `build.roles.scoring_engine_direct_gain`
   - a literal +Mult Joker must expose positive `direct_scoring_gain` / `direct_scoring_value` through B3 whole-build score projection;
   - structural/Bond labels are not sufficient evidence for a scoring foothold.
2. `build.roles.economy_not_direct_scoring`
   - an economy-only Joker must expose zero direct scoring gain while retaining positive contextual build value;
   - economy/support evidence may matter strategically but cannot manufacture chips or Mult.

Batch 1 changes semantic coverage only. No production code or tuning values changed.

Expected benchmark if both pass: **44/44**, with `BUILD_COHERENCE` increasing from 2/2 to 4/4.

---

# EXACT NEXT ACTION

Validate Phase-3 Batch 1 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 44/44 green

Continue Phase 3 with scaling evidence versus already-realized scoring power. Add cases only for concrete evidence/authority failure classes; do not tune numerical weights.

### If either Batch-1 case fails

Classify whether the B3 evaluator is conflating direct scoring with contextual support/economy evidence or whether the fixture exposes a modeling gap. Fix the smallest canonical B3 owner. Do not add D2/D14 rescue wrappers.

---

# PHASE ORDER

1. **Phase 0 — authority consolidation** — COMPLETE
2. **Phase 1 — D1 survival semantic expansion** — COMPLETE
3. **Phase 2 — simple shop survival** — COMPLETE
4. **Phase 3 — coherent build evidence/authority quality** — ACTIVE
5. **Phase 4 — complex packs/consumables/vouchers/economy audit**
6. **Phase 5 — live validation**
7. **Phase 6 — numerical tuning only after semantics are trustworthy**

Future stake/deck progression remains blocked until Red/White competence passes.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- Phase-0 D1 ownership migration queue
- Phase-1 semantic expansion beyond five validated batches
- Phase-2 simple-shop expansion beyond four validated batches
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
