# Balatro Live Integration

## Purpose

The live integration connects the Python decision framework to the actual Balatro process without embedding agent intelligence into the game integration layer.

BalatroBot is used only as the external game-control API. It supplies live state and executes requested game operations. Decision-making, search, evaluation, planning, and deck-specific strategy remain inside this repository.

## Architecture

```text
Balatro
    |
    | Lovely + Steamodded + BalatroBot
    | JSON-RPC 2.0 over HTTP
    v
BalatroBotBridge : BalatroLiveBridge
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

- **Lovely** injects the modding/runtime layer into Balatro.
- **Steamodded** loads the BalatroBot mod.
- **BalatroBot** exposes Balatro runtime state and native game controls through JSON-RPC.
- **`BalatroBotBridge`** owns the HTTP/JSON-RPC transport and maps generic live commands to BalatroBot methods.
- **`BalatroStateTranslator`** converts BalatroBot gamestate responses into the existing `BalatroState` model.
- **`RedDeckAgent`** remains the decision-making brain and does not depend on BalatroBot-specific details.
- **`BalatroActionExecutor`** converts selected `BalatroAction` objects into indexed live-game commands.

## Automated Setup

Python dependencies are installed normally:

```powershell
pip install -r requirements.txt
```

Balatro-side integration dependencies are installed with:

```powershell
py -m games.balatro.setup
```

The setup command:

1. detects the Steam Balatro installation, including secondary Steam libraries;
2. downloads the current Lovely release for the detected platform;
3. installs Lovely into the Balatro game directory;
4. downloads and installs the current Steamodded release;
5. downloads and installs the current BalatroBot release;
6. verifies all required files are present.

Use `--balatro-dir` when Balatro cannot be auto-detected, `--mods-dir` to override the mod directory, and `--force` to reinstall the integration dependencies.

On Windows, `py -m games.balatro.live` automatically starts `Balatro.exe` when the BalatroBot API is not already available. It sets the same `BALATROBOT_*` environment variables consumed by the BalatroBot mod, so `uvx balatrobot serve` is not required.

## Dependency Boundary

Lovely, Steamodded, and BalatroBot remain upstream runtime dependencies. Their source code is not vendored into this repository. The bootstrapper downloads their official GitHub releases into the locations required by Balatro.

The default API endpoint is:

```text
http://127.0.0.1:12346
```

The integration uses BalatroBot's public JSON-RPC API for operations including:

- game-state acquisition;
- starting and restarting runs;
- blind selection and skipping;
- playing and discarding cards;
- buying, selling, rerolling, and leaving shops;
- using consumables;
- cashing out completed rounds;
- advancing to the next blind.

No BalatroBot decision or strategy logic is used.

## State Mapping

BalatroBot returns structured areas for the hand, remaining deck, Jokers, consumables, shop cards, vouchers, packs, and booster contents. Cards in an area are addressed by their 0-based position.

The translator maps the live schema into framework concepts, including:

- deck and stake;
- ante and round;
- money and blind progress;
- hands and discards remaining;
- playing cards and modifiers;
- poker-hand levels;
- consumables;
- current/selectable blind information.

Framework cards and consumables retain the corresponding live area index as `live_id` so a selected framework action can be sent back to BalatroBot.

## Synchronization

BalatroBot actions return the settled game state after the operation. `BalatroBotBridge` normalizes these responses into `LiveBalatroSnapshot` objects and assigns a local monotonically increasing sequence whenever the observed game state changes.

`BalatroLiveSynchronizer` uses this sequence and phase filtering to avoid acting repeatedly on the same state.

## Running the Agent

After setup:

```powershell
py -m games.balatro.live
```

The default target is Red Deck / White Stake. Useful options include:

```text
--seed SEED
--endpoint URL
--balatro-dir PATH
--fast
--headless
--no-launch
```

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
10. Dependency bootstrap and launch.
11. End-to-end autonomous loop.

The v0.9 milestone proves that the agent can autonomously operate the actual game. Winning Red Deck White Stake is the v1.0.0 completion criterion.
