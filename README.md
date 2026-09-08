# game-ai-framework

A general framework for building autonomous AI agents for different games.

## Development

- [Roadmap](ROADMAP.md) — **single source of truth** for the active Balatro development path, exact checkpoint, blockers, CI gates, and next implementation task.
- [Changelog](CHANGELOG.md) — completed milestones and notable implementation changes.

### Balatro development workflow

The active Red Deck / White Stake competence branch is:

```text
feat/v1.0-red-white-competence
```

Continuation work should begin by reading the current `ROADMAP.md` and verifying the branch head. Repository state is authoritative; chat/session summaries are only navigation aids.

Development is done in small exact slices:

1. audit vanilla/source behavior and the existing canonical owner;
2. patch the canonical owner rather than adding approximation/rescue layers;
3. add focused deterministic regressions and fail-closed tests;
4. push the coherent slice;
5. gate it through GitHub Actions;
6. inspect the actual pytest log/count and confirm the intended tests were selected;
7. mark the slice GREEN and synchronize `ROADMAP.md` only after that gate passes.

Unsupported or incompletely owned mechanics stay unavailable. Do not broaden the training mask merely for convenience.

### Deterministic Balatro tests

Work Chat uses GitHub Actions as the authoritative deterministic pytest executor when no local repository runtime is available:

```text
.github/workflows/balatro-l3.yml
```

Current deterministic command:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

A workflow conclusion of `success` is not sufficient by itself: inspect the job log's final pytest line and verify that newly added test families were selected rather than deselected.

Do not ask for manual/local deterministic pytest when this workflow can answer the question. User-run Windows/Balatro validation is reserved for genuinely live-only integration or parity questions.

Exact development and CI procedures, source pins, fail-closed rules, live-validation policy, and current work are maintained in [ROADMAP.md](ROADMAP.md).

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
