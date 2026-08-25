# game-ai-framework

A general framework for building autonomous AI agents for different games.

## Development

- [Changelog](CHANGELOG.md) — completed milestones and notable implementation changes.
- [Roadmap](ROADMAP.md) — current milestone status and remaining work.

## Balatro

Strategy references:

- [Strategy system](docs/balatro/BALATRO_STRATEGY_SYSTEM.md)
- [Strategy formation](docs/balatro/BALATRO_STRATEGY_FORMATION.md)
- [Strategy catalogue](docs/balatro/BALATRO_STRATEGY_CATALOGUE.md)
- [Relationships and motifs](docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md)
- [Runtime policy authority](docs/balatro/RUNTIME_POLICY_AUTHORITY.md)

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Install the Balatro integration dependencies (Lovely, Steamodded, and BalatroBot):

```powershell
py -m games.balatro.setup
```

Run the live Balatro agent:

```powershell
py -m games.balatro.live
```

On Windows, `BalatroAgentToggle.bat` keeps the ordinary win-first behavior. Use
`BalatroAgentCollectionToggle.bat` for the opt-in collection-first profile mode;
an explicitly undiscovered visible item then outranks Bond/composition strategy,
economy, and current-run win probability.

The agent still turns itself off at the first Ante-8 win. To continue into
Endless for later-Ante collection requirements, click **Continue** in Balatro and
then start either toggle again. The new supervisor resumes that already-won run
until the next real game-over state.
