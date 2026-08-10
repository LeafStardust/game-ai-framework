# Balatro Live Integration

## Purpose

The production Balatro integration connects the Python decision framework to the normal Steam version of Balatro **without modifying or injecting into the Balatro process**.

The long-term target is an agent that plays the same visible game a human plays:

```text
Steam Balatro
    |
    | pixels
    v
External Observer
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
External Input Controller
    |
    | normal mouse / keyboard events
    v
Steam Balatro
```

This keeps the production game process unmodified and allows runs to use the normal Steam profile, save data, unlock progression, and achievement system.

## Production Architecture

```text
Unmodified Steam Balatro
        |
        | window capture
        v
BalatroExternalObserver
        |
        +--> UI/phase detector
        +--> card recognizer
        +--> HUD/state extractor
        +--> shop/blind/joker/consumable recognizers
        |
        v
BalatroStateTranslator
        |
        v
BalatroState
        |
        v
RedDeckAgent
        |
        v
BalatroAction
        |
        v
BalatroExternalActionExecutor
        |
        +--> screen-coordinate mapper
        +--> mouse controller
        +--> keyboard controller
        |
        v
Unmodified Steam Balatro
```

The production boundary is strict:

- no Lovely requirement;
- no Steamodded requirement;
- no BalatroBot requirement;
- no runtime Lua injection;
- no reading Balatro process memory;
- no native in-game API calls for action execution.

The agent observes pixels and acts through normal operating-system input events.

## Shared Live Interfaces

The live integration remains backend-independent. The existing bridge, snapshot, translator, executor, recovery, runner, and telemetry concepts are retained so alternate observation/control implementations can share the same agent code.

The deck agent must not know whether a state came from:

- a simulator;
- a development API backend;
- external visual observation.

Likewise, the decision system returns `BalatroAction` objects rather than mouse coordinates.

This separation is required for the general game framework: game-specific sensing and control belong in the adapter layer, while strategy remains in the agent/decision layer.

## External Observation

The Windows production observer will locate the Balatro window and capture only its client area.

Captured frames are normalized into a logical viewport so recognition and coordinate mapping do not depend directly on the user's screen position or window resolution.

The observer is responsible for extracting enough visible information to construct a useful `BalatroState`, including:

- current game phase;
- hand cards;
- remaining visible HUD information;
- ante and round;
- blind and required score;
- current score;
- money;
- hands and discards remaining;
- Jokers;
- consumables;
- shop contents;
- blind-selection state.

Recognition should expose confidence where appropriate. Low-confidence observations must cause re-observation or recovery rather than an unsafe click.

## External Input

The production controller translates framework actions into normal mouse and keyboard operations.

Examples:

```text
PLAY_CARDS
    -> map selected framework cards to current visible card positions
    -> click those cards
    -> click Play Hand

DISCARD_CARDS
    -> map selected framework cards to current visible card positions
    -> click those cards
    -> click Discard

BUY_JOKER
    -> locate the selected shop item
    -> click Buy
```

Coordinates are derived from the current normalized viewport and the current observation, not stored as fixed absolute desktop coordinates.

After every mutating action, the runner waits for visual confirmation of the expected transition before choosing another action.

## Development Oracle: BalatroBot

BalatroBot remains supported as an **optional development and testing backend**.

It is useful for:

- comparing visual recognition against structured internal state;
- generating labeled screenshots/state pairs;
- debugging state translation;
- exercising decision logic without relying on visual recognition;
- validating that an externally inferred state matches the real underlying state during development.

Its architecture is:

```text
Balatro
    |
    | Lovely + Steamodded + BalatroBot
    v
BalatroBotBridge
    |
    v
BalatroState / BalatroAction
```

BalatroBot does not provide agent strategy; however, because it uses an injected mod/API, runs made through it **do not count** toward v0.9.0 or later deck/stake completion.

The automated Lovely/Steamodded/BalatroBot setup code may remain for this optional development mode.

## Steam Progression Requirement

Production milestone runs must use the user's normal Steam copy and normal Balatro profile/save data.

The agent should therefore behave like an external human input device from Balatro's perspective. If the agent legitimately satisfies a normal in-game unlock or Steam achievement condition during a production run, the integration must not intentionally suppress or replace that progression mechanism.

No milestone depends on artificially unlocking content or editing save data.

## Synchronization

The external backend cannot assume an action completed simply because a mouse event was sent.

The synchronization loop is:

1. observe a stable frame/state;
2. choose one framework action;
3. execute the corresponding input sequence;
4. wait for a visible state change or expected phase transition;
5. re-observe and validate;
6. only then make the next decision.

Timeouts and low-confidence observations enter recovery rather than issuing repeated mutating input blindly.

## Production Running Target

The final production command should remain simple, for example:

```powershell
py -m games.balatro.live
```

The default target remains Red Deck / White Stake.

The production command should launch or focus the normal Steam Balatro installation and use the external backend by default. A development/API backend may be selected explicitly for debugging.

## v0.9 Task Boundaries

1. Shared live integration abstractions.
2. Steam Balatro window discovery and tracking.
3. External frame capture and normalized viewport.
4. Visual phase/state recognition.
5. Hand/card recognition.
6. HUD, blind, Joker, consumable, and shop recognition.
7. External state to `BalatroState` translation.
8. Normal mouse/keyboard action execution.
9. Visual synchronization and recovery.
10. Run start/restart through normal UI controls.
11. End-to-end autonomous external loop.
12. Validation on an unmodified Steam Red Deck White Stake run.

The v0.9 milestone proves that the agent can operate the normal Steam game externally. Winning Red Deck White Stake is the v1.0.0 completion criterion.
