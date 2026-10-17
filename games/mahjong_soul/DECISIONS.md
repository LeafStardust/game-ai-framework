# Read-only decision interface

`live.runtime.decision` packages a current reader snapshot for a future policy and validates its proposed intent. It does not choose actions, import a mouse backend, construct click plans or enable input.

```python
from games.mahjong_soul.live.runtime.decision import decision_request, validate_proposal

request = decision_request(reader.snapshot())
# A policy may choose one exact entry from request["actions"].
proposal = {
    "version": 1,
    "request_id": request["request_id"],
    "board_token": request["board_token"],
    "action": chosen_action,
}
# Drain capture again before validating the returned proposal.
validated = validate_proposal(request, proposal, reader.snapshot())
assert validated["executable"] is False
```

A request contains an independent versioned observation, unique request ID, exact board token, local monotonic issue/expiry times, and normalized server-offered actions. Default lifetime is two seconds. Requests are ephemeral within the current process/boot, not reusable saved commands. Callers must independently establish live capture freshness; creating a request from a ready saved snapshot does not make that snapshot live.

Supported intent kinds are `discard`, `chi`, `pon`, `closed_kan`, `open_kan`, `added_kan`, `riichi`, `tsumo`, `ron` and `skip`. Discard/Riichi/win intents retain exact tile identity. Call intents retain exact server combination strings, including red fives; opponent calls also include the source seat and called tile. Multiple combinations are distinct semantic choices, without claiming their choice-panel coordinates are supported. Skip is exposed only for the supported opponent call/win offer families.

Normalization checks current own operation ownership, known operation codes, contribution counts in hand, red/ordinary-five discard restrictions, Chi sequence and source seat, uncalled opponent discards, an existing matching Pon for added kan, and the known winning draw/source for win intents. It trusts the server to determine Mahjong legality such as yaku and furiten rather than implementing a second rules engine. Unsupported operation codes (including unimplemented three-player North extraction), duplicate codes and malformed supported combinations block the request. Raw operations remain available in the observation for diagnostics.

Proposals must have exactly `version`, `request_id`, `board_token` and `action`. Validation rejects expired requests, changed connections/generations/rounds/steps/operations/hands, unready or closed state, stale request IDs, arbitrary coordinates and any action absent from the freshly recomputed offer. Editing a request's candidate list cannot authorize a new action. A validated intent is an independent object explicitly marked nonexecutable; execution must still pass through current visual binding, calibrated geometry, capture freshness and the shared input controller. No proposal consumption or execution ledger is implied by this read-only validator.

## Validation evidence

Forty targeted tests initially covered request/proposal boundaries and all supported action families. Offline replay of the local 2026-10-17 capture produced requests for 131 unique decision-bearing boards with zero normalization rejections: 761 discard intents, ten Pon, nineteen Chi, five Ron, one added kan and twenty-five Skip intents. This exercises normalization on recorded data only; no agent policy or live automatic execution was used.

Next is a policy-facing adapter and offline decision/replay evaluation. Automatic execution remains a separate integration requiring verified screen-to-tile/action binding.


## Policy adapter and offline evaluation

The [Mahjong policy package](../../agents/mahjong_soul/README.md) now implements the policy boundary, deterministic integration baseline and aggregate offline evaluator. Every policy receives an isolated request and its proposal is revalidated against a current snapshot; policy exceptions do not produce fallback input. The existing capture yielded 131 validated baseline proposals with zero failures. No live policy consumer or mouse execution is connected.
