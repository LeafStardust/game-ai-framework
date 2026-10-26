# Tenpai Kan commitment fix ? October 26, 2026

The reviewed batch completed all three games and both restarts with no fatal halt: second at 19,900 (three wins, two deal-in events), first at 71,100 (four wins, no deal-ins), second at 40,300 (two wins, one deal-in event). All 220 submitted gameplay actions and all 66 assist changes were confirmed. Median input latency was 1.364 seconds; maximum 4.306 seconds; 144 of 220 actions were within 1.5 seconds.

## Missed offer

The reader correctly exposed a discard-plus-added-Kan offer in a valuable open Tenpai hand. The committed-ready shortcut returned discard before Kan evaluation, and Auto Discard was enabled. Therefore the earlier Kan-only exception fix did not address this separate path. The local saved decision now selects the exact added-Kan combination in ready_hand_kan mode.

Evaluate offered Kan before returning a committed-ready draw discard. Remove the blanket committed-ready Kan rejection. For ready hands, require the candidate to remain ready, preserve the legal winning-tile set and retain scored value, in addition to existing wall, ukeire, Yaku and special-hand checks. Accepted Riichi may evaluate an explicitly offered concealed Kan; added/open Kan remain excluded after declaration. Eligible candidates and wait-preservation rejections are recorded in kan_evaluations.

## Client switches

Before committing client C/D, check for a concealed triplet with a still-unseen fourth copy, a current quad, or an existing Pon whose fourth tile is held or still unseen. Keep Skip Calls and Auto Discard OFF in those cases so the client cannot consume the choice before policy evaluation. Apply the same condition to accepted-Riichi preferences and the follower's Riichi overrides. Once the fourth tile is publicly unavailable and no other Kan possibility remains, ordinary C/D commitment can resume.

This conservatively reduces C/D usage: an unseen fourth copy may be in an opponent hand or the dead wall. It preserves the ability to evaluate a future Kan rather than promising every potential fourth tile is drawable. The policy still checks the actual server offer and does not automatically Kan every Tenpai hand.

Validation uses synthetic added-Kan-ready hands, future fourth-tile availability, accepted-Riichi C/D preferences, and discard-plus-concealed-Kan offers after Riichi. The actual missed local offer now selects Added Kan with C/D disabled. No private hand fixture was published. Existing native visual and server-confirmation guards remain in place; no agent or game was started. Live delivery and the switch-preparation timing need the next normal user-started three-game batch.
