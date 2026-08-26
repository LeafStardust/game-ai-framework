# Balatro Live Validation Gate

Date: 2026-08-27

This gate starts after deterministic Red/White validation completed locally with:

```text
2647 passed, 1 skipped
```

The sole skip came from an empty parametrization over `BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS`. That set is currently empty and the same test module already proves exhaustive/disjoint Tarot classification, so the zero-case parametrized test provided no current coverage. Commit `2881bfe` removes it rather than carrying a permanent meaningless skip.

No tests or live games were run by the assistant.

## Live blocker 1 — first SHOP decision does not complete

Observed production attempt:

- session: `balatro-20260826T170420Z-1cee5969`
- attempt: `balatro-20260826T170420Z-1cee5969-attempt-001`
- Red Deck / White Stake
- Ante 1 / Round 1
- SHOP after the first blind
- money: $9
- owned Jokers: 0 / 5

The uploaded JSONL reaches a successful `END_ROUND` transition into a fully settled SHOP and then contains no SHOP `decision` event. The supervisor remains `THINKING`, so the blocker occurs during policy computation before bridge execution.

Observed visible shop state included:

- Zany Joker, $4
- 8 Ball, $5
- Buffoon Pack, $4
- Celestial Pack, $4
- Hieroglyph, $10
- authoritative public eligible Joker generation pools
- authoritative public Tarot/Spectral generation pools

This rules out a missing settled checkpoint or a failed shop click as the initial cause.

### Root cause

The final Celestial D8 wrapper in `planet_pack_fallback_policy.py` evaluated `_celestial_expected_selection_utility()` before its authoritative hand-development headroom/reserve veto.

For the observed first shop:

- there is no pinned hand goal;
- no hand has the minimum three observed plays required by `_observed_hand_goals()`;
- there is no Planet-use scaler;
- therefore `_celestial_headroom(state) == 0` and the pack must be `HOLD` regardless of its finite Planet expectation.

Nevertheless the old order first enumerated the public eligible Planet pool and repeatedly deep-copied/scored literal before/after states. That work could not alter the eventual HOLD and was large enough to block interactive shop progression.

### Repair

- commit `3cc694d` adds `celestial_shop_headroom_fast_path.py`;
- commit `068c946` installs that fast path from the final Red/White correction layer, after existing D8/Celestial wrappers;
- Celestial states that already fail the exact existing headroom or reserve condition return `HOLD` immediately;
- states that can still buy delegate unchanged to the full finite public-Planet expectation;
- no threshold, utility, hidden-state assumption, RNG access, or acquisition semantics were changed.

Validation status: **pending user local deterministic rerun and fresh three-attempt live baseline**.

## Current commands

Deterministic suite:

```powershell
python -m pytest tests/balatro -q
```

Three-attempt Red/White production baseline:

```powershell
.\BalatroAgentToggle.bat --three
```

## Gate rule

Do not begin numerical calibration/Optuna until the deterministic suite remains green on this live-response repair and the fresh three-attempt baseline completes SHOP decisions without semantic/runtime stalls.
