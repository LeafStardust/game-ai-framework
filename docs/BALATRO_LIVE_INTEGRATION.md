# Balatro Live Integration

## Purpose

The live integration connects the Python decision framework to the actual Balatro process without embedding agent intelligence into the game mod.

## Architecture

```text
Balatro (LÖVE/Lua)
    |
    | Steamodded/Lovely bridge mod
    | snapshots / commands
    v
BalatroLiveBridge
    |
    +--> BalatroStateTranslator --> BalatroState
    |                               |
    |                               v
    |                         RedDeckAgent
    |                               |
    |                               v
    +<-- BalatroActionExecutor <-- BalatroAction
```

The responsibilities are deliberately separated:

- **Lua bridge mod** reads Balatro's internal state and performs game-native interactions.
- **`BalatroLiveBridge`** owns transport only. It does not understand strategy.
- **`BalatroStateTranslator`** converts live snapshots into the existing `BalatroState` model.
- **`RedDeckAgent`** remains the decision-making brain and should not know whether its state came from simulation or the live game.
- **`BalatroActionExecutor`** converts selected `BalatroAction` objects into live-game commands.

## Integration Surface

The in-game bridge will use Steamodded/Lovely because Balatro exposes its runtime state through Lua globals such as `G`, `G.GAME`, `G.STATE`, and the event manager. This avoids making screen recognition and mouse-coordinate automation the primary source of truth.

The initial transport will use JSON messages between the Lua bridge and Python. The Python interfaces do not depend on a specific transport so the implementation can later move to sockets or another IPC mechanism without changing agent code.

## Protocol Rules

Every snapshot and command has a monotonically increasing `sequence` value. This is used to prevent the Python agent from acting twice on the same live state and to detect stale messages.

A snapshot contains:

- current live phase/state identifier;
- whether the game reports that state as complete/stable;
- a payload containing the game data required by the translator.

A command contains:

- the snapshot sequence it responds to;
- a framework action name;
- action-specific payload such as selected card identifiers or shop targets.

## v0.9 Task Boundaries

1. Real-game integration architecture.
2. Live Balatro state acquisition.
3. Live state to `BalatroState` translation.
4. `BalatroAction` to live-game input execution.
5. Synchronization and phase detection.
6. Shop and consumable interaction.
7. Blind and round transitions.
8. Run start/restart.
9. Recovery handling.
10. End-to-end autonomous loop.

The v0.9 milestone proves that the agent can autonomously operate the actual game. Winning Red Deck White Stake is the v1.0.0 completion criterion.
