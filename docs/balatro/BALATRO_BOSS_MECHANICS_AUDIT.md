# Balatro Boss Mechanics Authority Audit

Status: implementation audit complete for Red/White competence; deterministic suite validation remains user-owned.

This document records where each vanilla Boss Blind mechanic is represented in the production Balatro agent. A boss does not need an entry in `live/boss_blind_integration.py` when its exact effect is already authoritative in live state or another transition/scoring layer.

## Authority rules

- Boss logic uses public game state only.
- `ChicotJoker` disables boss mechanics through `boss_blind_disabled_by_owned_jokers()`.
- Live blind target, hands, discards, card debuffs, forced selection, and boss-owned state are authoritative where Balatro exposes them.
- Hypothetical D1 branches explicitly model effects that would otherwise only appear after a real action.
- Visibility-only bosses are deterministic pass-throughs because this project explicitly permits the underlying rank/suit identity exposed by process memory.
- Missing data fails closed; no boss target, random branch, or tie-break is invented.

## Boss inventory

| Boss | Production authority |
| --- | --- |
| The Hook | `live/final_joker_outcomes.py` branches uniformly over the forced random two-card discard before scoring; `hook_planner_integration_policy.py` preserves each branch-specific hand through deeper D1 search. |
| The Ox | `boss_trigger.py` resolves the authoritative round-start most-played hand; `live/final_joker_outcomes.py` sets money to $0 before Joker scoring when triggered. Unresolved legacy ties fail closed. |
| The House | Visibility-only; underlying public process-memory card identity remains usable by project contract. |
| The Wall | The enlarged blind requirement is already the authoritative live `Blind.requirement`; no score transform is required. |
| The Wheel | Visibility-only; underlying card identity remains usable by project contract. |
| The Arm | `live/boss_score_transform.py` scores at the lowered effective hand level; `live/final_joker_outcomes.py` persists the hand-level loss after scoring. |
| The Psychic | Short plays remain legal but score zero through `boss_hand_is_debuffed()` / `BossBaseScoreScorerMixin`; D1 can still use them as burn/cycle actions. |
| The Goad | Authoritative per-card `debuffed` state suppresses affected card scoring/effects. |
| The Water | Authoritative live `discards_remaining` is zero; normal D1 resource legality therefore applies without a separate boss transform. |
| The Eye | Blind-owned played-hand history is observed when available; repeated hand types score zero and D1 filters them while unused legal types remain. |
| The Mouth | Blind-owned first accepted hand is observed/projected; other hand types score zero and D1 recovery targets the locked type. |
| The Plant | Authoritative per-card `debuffed` state suppresses face-card effects. |
| The Serpent | `serpent_draw_policy.py` forces exactly three cards after either Play or Discard in hypothetical D1 branches. |
| The Pillar | Authoritative per-card `debuffed` state carries previously-played-card debuffs into scoring and draw signatures. |
| The Needle | Authoritative live `hands_remaining` is one; normal D1 resource legality handles the restriction. |
| The Head | Authoritative per-card debuff state plus the existing Head evaluator cover Hearts-debuff execution. |
| The Tooth | `live/final_joker_outcomes.py` subtracts $1 per selected played card before independent Joker scoring, so Bull/Bootstraps see post-Tooth cash. |
| The Flint | `live/boss_score_transform.py` halves base Chips and Mult with Balatro rounding before ordinary scoring effects. |
| The Mark | Visibility-only; underlying face-card identity remains usable by project contract. |
| Amber Acorn | Actual live post-shuffle Joker order is authoritative; no hypothetical fake order is introduced. |
| Verdant Leaf | Actual live card debuffs remain authoritative until the dedicated emergency-sale path removes the condition; Chicot bypasses the boss. |
| Violet Vessel | The enlarged blind requirement is already authoritative live state; no separate score transform is required. |
| Crimson Heart | `live/crimson_heart.py` / boss integration models the currently disabled Joker and branches the next random disabled Joker where a hypothetical transition requires it. |
| Cerulean Bell | Forced-selection state is observed on cards; root and recursive D1 actions obey it, and hypothetical redraws branch over possible next forced selections. |

## Result

The boss audit found no remaining vanilla Red/White boss mechanic that requires a new duplicate handler. The apparent omissions from `_BOSS_RULES` are intentional where the mechanic is already represented by:

1. authoritative live resources/requirements/debuffs,
2. the final score transition layer,
3. a dedicated planner-transition policy, or
4. the project's explicit visibility contract.

The implementation audit is complete. Regression validation of the newest Verdant Leaf / Crimson Heart and later semantic changes remains separate and must be performed by the user before a new live baseline is considered authoritative.
