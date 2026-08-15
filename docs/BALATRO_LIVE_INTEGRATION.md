# Balatro Live Integration

## Purpose

The Balatro live integration connects the Python decision framework to the Steam version of Balatro through the injected BalatroBot API.

The runtime stack is:

```text
Steam Balatro
    |
    | Lovely + Steamodded + BalatroBot injection
    v
BalatroBot JSON-RPC API
    |
    v
BalatroBotBridge
    |
    v
BalatroStateTranslator
    |
    v
BalatroState
    |
    v
Deck Agent / Decision System
    |
    v
BalatroAction
    |
    v
BalatroBotBridge
    |
    v
Steam Balatro
```

The injected backend is the production backend for Balatro in this project. External screen capture, computer-vision state extraction, and mouse/keyboard control are not part of the current architecture.

## Runtime Components

### BalatroBotBridge

`BalatroBotBridge` owns JSON-RPC communication with the injected BalatroBot mod. It is responsible for:

- health and connectivity checks;
- structured game-state requests;
- translating framework actions to BalatroBot RPC calls;
- tracking snapshot sequence changes;
- exposing RPC failures as framework-level exceptions.

### BalatroStateTranslator

The translator converts BalatroBot's structured payload into `BalatroState`.

The translation layer should be the only place that knows the exact BalatroBot payload schema. Game strategy should consume `BalatroState`, not raw RPC payloads.

### BalatroLiveRunner

The live runner owns the autonomous loop:

1. start or restart a run;
2. obtain a structured snapshot;
3. translate it into `BalatroState`;
4. determine legal framework actions for the current phase;
5. let the deck agent choose an action;
6. send the corresponding RPC command;
7. observe the resulting state;
8. repeat until `GAME_OVER`.

### Lifecycle, Recovery, and Telemetry

Lifecycle helpers handle run start/restart and phase-transition RPCs. Recovery wraps bridge operations so transient failures can be retried or surfaced consistently. Telemetry records live decisions, state transitions, errors, and run results.

## Setup

The supported Balatro integration stack is:

- Lovely;
- Steamodded;
- BalatroBot.

The setup module may install and validate these components automatically.

## v0.9 Scope

v0.9 is complete when the injected live integration can autonomously operate a Red Deck / White Stake run from start to `GAME_OVER` without manual gameplay input.

Winning is not required for v0.9. The first successful White Stake win belongs to v1.0.0.

The remaining v0.9 work is primarily integration correctness rather than game strategy:

1. complete BalatroBot protocol/capability compatibility checks;
2. complete `BalatroState` translation for every field required by decisions;
3. unify phase/lifecycle actions with the framework action model;
4. support blind selection and skipping without special-case gaps;
5. validate all required action RPC mappings;
6. make phase handling robust across the full run lifecycle;
7. improve synchronization, stall detection, and recovery;
8. add a real injected end-to-end smoke test;
9. validate one full autonomous Red Deck / White Stake run to `GAME_OVER`.

## Boundary With v1.0

v0.9 proves that the framework can reliably observe and control the live injected game.

v1.0 adds the first complete Red Deck strategy, including shop decisions, Joker selection, consumable strategy, blind strategy, economy management, deck building, and the first successful unseeded White Stake win.
