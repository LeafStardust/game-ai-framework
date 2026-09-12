# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Objective

**Maximize P(clear Ante 8 | Red Deck, White Stake, normal mode).**

The project has pivoted from manually tuned Bond-value strategy to reinforcement learning in a fast deterministic Balatro environment. Existing deterministic mechanics, legality, public-state observation, tactical hand play, candidate projection, telemetry, and useful Bond-derived features remain assets. Manual Bond coefficient tuning is retired as the primary competence path.
## Non-negotiable contract

- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported or inexact transitions stay absent from the training mask.
- Prefer canonical ownership over wrappers, rescue layers, duplicated mechanics, or approximations.
- Training code must not redefine Balatro mechanics for convenience.
- Simulator shortcuts are allowed only when behaviorally equivalent at the modeled boundary and regression/parity covered.
- Model checkpoints are artifacts, not strategy source of truth.
- Do **not** start PPO or observation training before exact environment semantics and representative live/simulator parity gates.
- Work Chat runs deterministic/static validation itself. GitHub Actions is authoritative when no local clone is available.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Permanent deck truth is `G.playing_cards`; never substitute `G.deck.cards`.
- Hidden physical draw order and face-down card/Joker identity-to-position mappings are not policy-visible.
- Python `random` is not Balatro RNG.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, `--five`, or plural `--attempts`; the sole canonical attempt-count interface is `--attempt N`.
- If context becomes insufficient to continue safely, **stop immediately rather than guessing**.

## Continuation procedure

For every continuation session:

1. read this file first;
2. verify current branch/HEAD before editing;
3. inspect canonical owners and pinned vanilla source for the next task;
4. check for intervening commits before writing;
5. treat chat/session summaries as navigation only; repository state is authoritative;
6. add focused fail-closed regressions for every new exactness slice;
7. push coherent completed commits;
8. inspect the actual CI pytest result, not only the workflow badge;
9. synchronize this roadmap after green slices.

Pinned vanilla source:

```text
GladdonT/balatro-source-code
895ab3a25bc6f513fa80885eb59951bf8e76bc55
```

Authoritative deterministic workflow:

```text
.github/workflows/balatro-l3.yml
```

Current CI selector:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2 or env_r3 or env_r4 or env_r5"
```

---

# Current checkpoint — 2026-09-11

```text
Branch: feat/v1.0-red-white-competence

R3 closure verification commit:
2e8daa4b64694cc22862f99ea16adea3c61c00f2
  docs(balatro): sync roadmap through R3 closure
GitHub Actions run 33982517717
2331 passed, 1595 deselected

R4 exact discard bridge:
c117ab054e8cebb8a402711cca46ed48fb076172
  feat(balatro): bridge public tactical discard
GitHub Actions run 33982555046
2335 passed, 1595 deselected

R4 production decision-engine wiring:
5d8565b6910eb9c77b8342465dc404bd6a902840
  refactor(balatro): wire R4 tactical decision engine
GitHub Actions run 33995495867
2336 passed, 1595 deselected

R4 ordinary Play lifecycle:
652b32624ae2feaad9e768baac9f505b386bb271
  feat(balatro): own ordinary R4 play lifecycle
GitHub Actions run 33999099418
GitHub Actions job 101394654137
2350 passed, 1595 deselected

R4 representative Boss tactical coverage:
98ab566071f0af94305ffaba5b9fa0482e25b4ad
  feat(balatro): admit exact Tooth tactical play
f8bc7aabafcd766fd9bcada15e8bef489977d7a5
  feat(balatro): admit exact Hook tactical play

e9408fa943bbc2609f3ee96e53318ba2ff2c874c
  feat(balatro): record public tactical trajectory evidence
0603f420ee7f7d1f235c21b0ea9debc7b72442e5
  fix(balatro): freeze tactical evidence snapshots

R5 tactical parity infrastructure:
7dd4f36341fd5624d05db2e7b59e808f81ceb5cd
  feat(balatro): add R5 tactical parity comparator
da7e4e9605d37584b116f28274bdb7fc91ac728a
  feat(balatro): adapt live run logs for R5 parity
GitHub Actions run 34005381429
GitHub Actions job 101411468974
2373 passed, 1595 deselected

0a657d961b13bac12371466418ff470c15e62a61
  feat(balatro): compare R5 tactical trajectories
GitHub Actions run 34005877151
GitHub Actions job 101412827495
2377 passed, 1595 deselected

R5 exact strategic reroll replay authority:
d82801c8
  feat(balatro): capture R5 live RNG replay authority
c9203f25
  feat(balatro): restore R5 reroll replay checkpoints
de1a53dc
  fix(balatro): require observed vouchers for reroll replay
e116bf09e0c13c6092dc57b7bc2dae5e7f9ee792
  feat(balatro): replay exact R5 shop reroll parity
GitHub Actions run 34022177202
GitHub Actions job 101456639275
2401 passed, 1595 deselected

R5 live paid-reroll capture wiring:
b15fab5fe2bec0080c383a009dbef4f00cc89e12
  feat(balatro): capture live R5 reroll parity
GitHub Actions run 34024889806
GitHub Actions job 101463994146
2409 passed, 1595 deselected

R5 paid-reroll live-fixture readiness repairs:
b092783e9bb44831e2333b5bf70439af4b37c785
  fix(balatro): admit depleted paid-reroll shops
fc65fa09855a7e3a2febf60c04c8a9ef9f86877a
  fix(balatro): expose reroll replay rejection cause
c3ed2b712fe3422c523ffe3e9ae67b604369facf
  fix(balatro): model shop consumable pool visibility
15db1dbc2d5fecd29d49c3ffa28b9bd6cb344562
  fix(balatro): observe consumable pool in production
9083d4170bad8d2ce799ec47debb585fe94d9943
  fix(balatro): admit Omen Globe for base shop parity
3f9ef026b768342aa18cbad4e5defda8b5a8bc1d
  fix(balatro): decouple exact reroll voucher capability
99a4776ce8d01b47fb0a460cdc31d5ea63558b2e
  test(balatro): cover Telescope paid reroll parity state
GitHub Actions run 34213635015
GitHub Actions job 102020161503
2419 passed, 1595 deselected

R5 first real paid-reroll fixture repair:
606c7b4535176e92f9bc87192cc9a049670a0d6e
  fix(balatro): align paid reroll with live parity
9fbfe70386e3141c565cd07c655decd5194dd1cb3
  test(balatro): align exact reroll regressions
GitHub Actions run 34217561085
GitHub Actions job 102032815831
2421 passed, 1595 deselected

Canonical attempt-count correction and branch-tree repair:
7b1fb06f7a307a2ac2d0fec8613f18c6eaeeb79d
  fix(balatro): restore branch tree after launcher update
GitHub Actions run 34218019368
GitHub Actions job 102034289630
2427 passed, 1595 deselected

R5 supported Joker purchase evidence and true headless replay:
256d56baf36f0d5a32b9aabf827cbbdc2643c3f5
  feat(balatro): add Joker purchase parity evidence
adfa8458fbee9f6b51db0f7b8b25e8ab36d0c56c
  test(balatro): seed R5 joker purchase replay
0183d09d729dad15f72948be0326a10432ecea07
  test(balatro): complete R5 Joker purchase fixture metadata
30b8ca49678f1826b92d8939d9337997d5275dbc
  test(balatro): replay R5 Joker purchase without normalization
8d6b64adc3ab2884d59e5d59a9d2a8f448f83ed5
  test(balatro): compare R5 purchase identity structurally
GitHub Actions run 34222351675
GitHub Actions job 102048209359
2431 passed, 1595 deselected

e2e4c23ea669283fc3991cc5bf6ad10920a22f9b
  test(balatro): replay real R5 Joker purchase fixture
6b93714d3ca496d6440be75f3b169e5b48b04cd3
  fix(balatro): normalize exact live Joker prices
a709b9c74e688f20ebaa82ba8fed5e02d2e231fa
  test(balatro): freeze exact live Joker price translation
GitHub Actions run 34229665010
GitHub Actions job 102072335608
2437 passed, 1595 deselected

R5 supported Voucher purchase evidence and live identity normalization:
e67d19d754c447f1dea116bcf82948dc7545c697
  test(balatro): cover R5 Voucher purchase parity
e792d007469b4440740ae5317fb024d82b2eda17
  fix(balatro): add Voucher parity evidence wrapper
36bbe5eb2f7057bb41d4846996c8efca9b466811
  fix(balatro): normalize live shop center identity
GitHub Actions run 34234881414
GitHub Actions job 102089904106
2443 passed, 1595 deselected

R5 first real supported Voucher-purchase fixture:
b4350d99e538d9c423724c6f2ba77bd079dfc70d
  test(balatro): replay real R5 Voucher purchase fixture
  intermediate CI exposed fixture gzip transport CRC only; 2443 prior tests remained green
4aba3b42f40f03b1d35dc58414d913e62537b369
  fix(balatro): preserve real Voucher fixture bytes
GitHub Actions run 34237730786
GitHub Actions job 102099701468
2445 passed, 1595 deselected

R5 blind-start replay prerequisites:
9af3cc3691b75b4aac178265124927537542630e
  fix(balatro): normalize exact playing-card live ids
2c2d96055b84a8791fafe53372446bbc25e54314
  test(balatro): freeze exact playing-card live ids
92d2a2abc6301c32fef2927c11eb76a3e6e2dd74
  test(balatro): select exact playing-card id regressions
GitHub Actions run 34250416208
GitHub Actions job 102143121535
2452 passed, 1595 deselected

R5 exact blind-start checkpoint restoration/replay:
a8ebd04f5988775f9decef031ba036af2543d222
  feat(balatro): replay exact blind starts
6d0441a0e36571f6cc162baae1e88f0e628d07fc
  test(balatro): admit exact live-id base deals
GitHub Actions run 34301741520
GitHub Actions job 102309893935
2460 passed, 1595 deselected

R5 opt-in production blind-start capture:
c46d29217a3f650033f6bf16a8a385555e414a24
  feat(balatro): capture live blind-start parity
2ac3ddd48fcb95651ffb1c33e59cd30d2144e774
  test(balatro): use semantic blind-start drift
GitHub Actions run 34302658025
GitHub Actions job 102312696793
2468 passed, 1595 deselected

R5 canonical blind-start capture launcher handoff:
833b2efe73e12cb50099f7928d5617b1266e839b
  fix(balatro): forward blind-start parity capture
GitHub Actions run 34303241025
GitHub Actions job 102314477860
2469 passed, 1595 deselected

R5 first live blind-start capture defect and exact-ID repair:
caed3305b7a66037873f64b1332e3bc6abc50df4
  fix(balatro): normalize live deck card ids
cedd0f114ff01899d13a9f9df641f3a37da8b3f0
  fix(balatro): preserve opaque fixture card ids
GitHub Actions run 34305345713
GitHub Actions job 102320769712
2470 passed, 1595 deselected

R5 first complete private blind-start capture and pending-requirement repair:
9d45292f072c248c00271f2e4e88df185ea9db63
  fix(balatro): observe pending blind requirement
GitHub Actions run 34332070925
GitHub Actions job 102402745553
2471 passed, 1595 deselected

R5 first real passing ordinary Small-Blind start fixture:
74a5acfa533932d407fa2032a051b49897667081
  test(balatro): replay real blind-start fixture
GitHub Actions run 34334451991
GitHub Actions job 102410451037
2473 passed, 1595 deselected

R5 first real ordinary Small-Blind cash-out fixture:
6e7c59c4b9c46f198ec56d0652670d05e7550218
  fix(balatro): replay ordinary blind cashout
8102cbddd58c80e79c797d6bd8573ccffce6018e
  test(balatro): align cashout fixture authority
c304f8d4b3d82bc53ba5eab545447a7f7bae04f2
  test(balatro): declare cashout reset authority
GitHub Actions run 34337142981
GitHub Actions job 102419085820
2476 passed, 1595 deselected

R5 exact Economy-Tag blind-skip capture/replay seam:
3236a67b2dfe2cdd5e32cb7b31d1231b6659b25d
  feat(balatro): capture exact blind skip parity
GitHub Actions run 34362156416
GitHub Actions job 102501607817
2486 passed, 1595 deselected

R5 live Economy-Tag skip settlement repair:
0966658fba8de7277c23ddfa8e3a1c07d718b793
  fix(balatro): await Economy Tag skip payout
GitHub Actions run 34367250892
GitHub Actions job 102519067100
2486 passed, 1596 deselected

R5 first real passing Economy-Tag blind-skip fixture:
9c0d5c68d36895fcb175f53c1b4004fee0d475a5
  fix(balatro): replay live Economy Tag skip
GitHub Actions run 34375666032
GitHub Actions job 102547699010
2488 passed, 1596 deselected

R5 canonical Buffoon pack public evidence seam:
9daea5a4a874f39b27790755e6d391ac21a720b1
  feat(balatro): add Buffoon pack parity evidence
GitHub Actions run 34377040125
GitHub Actions job 102552347902
2495 passed, 1596 deselected

R5 opt-in exact Buffoon pack private capture:
ccb1cc887af1fea3be24f595119156f6caf0cb2b
  feat(balatro): capture Buffoon pack parity
GitHub Actions run 34378808960
GitHub Actions job 102558247537
2507 passed, 1596 deselected

R5 first real Buffoon choice fixture and used-Joker pool repair:
6f0a57ce890494326c11f1f25f33b3888be1abc4
  fix(balatro): replay live Buffoon choice pool
19c3af33a4c0a090c31330d097769a6dc8fa29aa
  test(balatro): use exact Buffoon offer pair
GitHub Actions run 34394979554
GitHub Actions job 102612318553
2510 passed, 1596 deselected

R5 canonical held-Planet public evidence seam:
17be3ae6517b65054c81d7094e36f54673beccf2
  feat(balatro): add held Planet parity evidence
GitHub Actions run 34396027499
GitHub Actions job 102615838664
2520 passed, 1596 deselected

R5 exact held-Planet private replay seam:
452222e7
  feat(balatro): capture held Planet parity state
GitHub Actions run 34398260070
GitHub Actions job 102623415051
2541 passed, 1596 deselected

R5 in-round held-Planet replay readiness:
b2c3750a
  test(balatro): assert canonical Planet hand key
GitHub Actions run 34413383953
GitHub Actions job 102672681684
2546 passed, 1596 deselected

R5 audited Joker-sale evidence/replay seam:
5a27e22b9894a34a222ef2a47634f3396afa5e57
  test(balatro): identify unsupported Joker sale
GitHub Actions run 34421799213
GitHub Actions job 102698626846
2557 passed, 1596 deselected

R5 pending-Boss public identity and exact start replay seam:
e185397aa44dd26762b296b710c5abd6237ad0cc
  feat(balatro): expose pending Boss parity state
GitHub Actions run 34423267134
GitHub Actions job 102703054698
2560 passed, 1596 deselected

R5 private post-deal draw-order replay authority:
73db93f5e095953520a197ccee85882ba3b1ab97
  feat(balatro): retain private blind draw order
GitHub Actions run 34424062376
GitHub Actions job 102705412026
2570 passed, 1596 deselected

R5 owned-deck composition parity:
e1aa7866b6bc6c538e041f41ba6db155f8dfbf41
  test(balatro): correct owned-deck composition fixture
GitHub Actions run 34458486597
GitHub Actions job 102810415392
2571 passed, 1596 deselected

R5 bounded Money Tree natural-fixture probe:
2026-09-10
  The bounded one-attempt probe exited before gameplay because the first-party bridge did not consume STATUS (`InjectedBridgeTimeoutError` while waiting for STATUS); no phase/checkpoint/run log was produced. Focused bridge tests remained green, and no natural Money Tree fixture was produced.

R5 GitHub Actions verification for the bounded Money Tree probe:
Commit c710cddd
GitHub Actions run 34508553737
GitHub Actions job 102976661662
  The job completed with failure in `Run deterministic Balatro suites`; setup and dependency steps passed. Exact pytest counts and the traceback are unavailable because the public logs return HTTP 403. The local deterministic selector remains the available evidence for this result. No root cause is claimed.

R5 newer GitHub Actions verification for the bounded Money Tree probe:
GitHub Actions run 34509660687
  The job completed with failure in `Run deterministic Balatro suites`, in the same deterministic step as run 34508553737. Public logs and the traceback are unavailable because the public logs return HTTP 403. The local deterministic selector remains the available evidence for this result. No root cause is claimed.

R5 latest GitHub Actions verification for the bounded Money Tree probe:
GitHub Actions run 34510243161
  The same `balatro-deterministic-tests` job failed in `Run deterministic Balatro suites` with generic exit code 1. Public logs and failure details are unavailable because the public logs return HTTP 403. No root cause is claimed.

R5 bounded launcher startup-failure handling:
19d81b5cc1997459d3e7e844bb048aa8817ca4cf
  fix(balatro): fail bounded launcher on startup failure
  The canonical `--attempt N` launcher now observes detached supervisor status
  until the first attempt is published, returns nonzero on authoritative OFF /
  bridge-readiness failure, preserves the supervisor reason, and leaves ordinary
  toggle behavior unchanged. Focused local validation: 24 passed across the
  launcher and bounded-supervisor tests; compileall passed for the three edited
  modules; `git diff --check` passed. GitHub Actions run 34520890482, job
  103017830178, was pushed and remained in progress when this checkpoint was
  synchronized; no remote pytest count is claimed yet.

R5 bounded launcher startup grace repair:
  The canonical bounded launcher now uses the existing supervisor startup
  stability timeout rather than a shorter 2-second readiness budget. The wait
  still fails immediately on authoritative OFF/failure and still requires
  `ON` with `attempt >= 1`; focused coverage proves an `ON`/`attempt=0` state
  can remain visible past 2 seconds and return once the first attempt is ready.
  Local validation: 15 passed, 0 failed, 0 deselected in
  `tests/balatro/test_balatro_env_r5_attempt_count_launcher.py` with
  `PYTHONPATH=.`.

R5 bounded launcher monitor-forwarding boundary repair:
  `toggle_agent` now accepts and forwards the existing `launch_live_monitor`
  keyword to `start_agent`, preserving ordinary toggle defaults. The canonical
  `--attempt 1` regression exercises `attempts_toggle.main` through the real
  `base_toggle.main` and `toggle_agent` boundary without launching a process.
  Focused validation: 14 passed, 0 failed, 0 skipped, 0 deselected across the
  launcher and bounded-supervisor regression files.

R5 startup status handoff repair:
  The canonical supervisor now publishes `STARTING` until the first settled
  public checkpoint has selected the run identity; `ON` remains reserved for
  the existing ready boundary immediately before autonomous decisions begin.
  This prevents an ON status from claiming action readiness while observer
  attachment, bridge validation, or startup stabilization is still pending.
  Focused validation: 27 passed, 0 failed, 0 skipped, 0 deselected across the
  supervisor, bridge pump/timeout, and canonical attempt launcher regressions.

R5 live-memory `G` cache process-identity repair:
  The canonical `WindowsProcessMemoryReader` now exposes the Win32 process
  creation timestamp, and `balatro_g_discovery` binds cached `G` addresses to
  both PID and that timestamp. Legacy/PID-only entries and entries whose live
  process identity cannot be read are rejected before reuse, so PID reuse cannot
  turn a stale Lua address into a misleading `LuaJITMemoryError` during observer
  startup. The repository's observed Windows runtime remains the non-GC64
  LuaJIT layout; no executable/archive revision mismatch was proven by available
  repository or runtime artifacts, and no live process was launched for this
  repository-only repair.
  Focused validation: 19 discovery/decoder tests passed; 36 observer/supervisor
  tests passed; roadmap selector passed with 2599 passed and 1601 deselected.

R5 live-agent bridge timeout diagnostics:
  The first concrete current no-movement failure remains a live-only
  `InjectedBridgeTimeoutError` while waiting for `STATUS`; the pending command
  was cancelled before Balatro consumed it. The canonical bridge timeout now
  records the command id, bridge/command/response paths, response presence, and
  timeout budget in the exception captured by the supervisor diagnostic log.
  No stale supervisor or monitor process was present during read-only
  inspection, and no control/process command was launched. Focused validation:
  2 passed, 0 failed, 0 skipped, 0 deselected in
  `tests/balatro/test_balatro_bridge_timeout_cleanup.py`.

R5 live-memory startup regression repair:
  `e47c5d539ef2478017d81b0ed1d071d6d73e6a3a` restored direct in-process
  `ReadProcessMemory` for normal `WindowsProcessMemoryReader.read()` calls.
  The bounded multiprocessing timeout helper remains available only when a
  caller explicitly supplies a timeout. Focused live-memory, G-discovery,
  phase-readiness, and supervisor validation passed with 28 tests green.
  The user subsequently confirmed that the existing bridge and agent attach
  path are running successfully from the first Ante 0 blind-select screen;
  no bridge rebuild or reinstall was required.

R5 live production run after startup repair:
  User-run artifact `balatro-20260911T023150Z-b5c096e6-attempt-001` completed
  through the operational live path with 294 events, 77 decisions, 37 blind
  outcomes, and 10 purchases. The run reached Ante 5 and ended with the
  terminal reason `game_over` at the Ante 5 Big Blind (`won=false`); this is
  confirmed live production execution, not a bridge/startup failure. Its
  purchases did not include `v_money_tree`, so it is not promoted as the
  natural Money Tree transition fixture. The next live gate remains a run
  that actually purchases Money Tree and captures its exact transition.

R5 latest live production artifact audit:
  `balatro-20260911T024403Z-4ce210a4-attempt-001` completed through the same
  operational live path with 213 events, 55 decisions, 20 blind outcomes, and
  4 purchases. It reached Ante 3 and ended with `game_over` at the Small Blind
  (`won=false`). Its only Voucher purchase was `v_wasteful`; it did not buy
  `v_money_tree`, so no Money Tree fixture is promoted from this run. At the
  synchronized checkpoint Balatro and the bounded supervisor are both OFF.

R5 five-attempt natural-fixture batch and Joker-sale promotion:
  User-run session `balatro-20260911T113953Z-d9e2aa91` completed all five
  bounded attempts through the operational live path. None purchased
  `v_money_tree`, and none emitted `USE_CONSUMABLE`, so the Money Tree and held
  Planet gates remain open. Attempt 4 did emit a current-HEAD exact-target
  `SELL_JOKER` boundary. The preserved fixture sells Jolly Joker at owned index
  1, credits money `$38 -> $39`, and removes only that Joker from the ordered
  inventory. Exact replay exposed that the headless sale owner did not mirror
  vanilla `Card:remove` clearing the sold center from `G.GAME.used_jokers`, so
  the observed generation pool re-admitted `j_jolly` while the simulator did
  not. The canonical sale owner now reuses the existing ordered generation-pool
  restoration owner after inventory removal; duplicate ownership and Showman
  behavior remain owned by that fail-closed path. Focused affected validation
  passed with **31 passed**. Commit
  `538ddd8501644e3e8c8581adc4828222118466fe` passed GitHub Actions run
  `34597576815`; the actual job log reports **2609 passed, 1603 deselected in
  94.37s**. This completes the audited natural Joker-sale gate without
  promoting any absent Money Tree or held-Planet evidence.

R5 second five-attempt natural-fixture batch:
  User-run session `balatro-20260911T124644Z-0ae208f7` completed all five
  bounded attempts through the production path. The attempts ended at Antes
  7, 4, 5, 2, and 4 respectively, all with `game_over`. No attempt purchased
  `v_money_tree`, so the natural Money Tree gate remains open. Attempt 3 used
  a held Saturn, but this batch was launched without the opt-in
  `--held-planet-parity-directory`; only the public run rows exist, not the
  private consumable-usage checkpoint required by the canonical replay seam.
  That Saturn boundary is therefore not promoted or reconstructed. No
  blind-start private sidecars were requested either, so Boss-start and
  strengthened draw-order gates also remain open. The next bounded command
  must enable both held-Planet and blind-start private capture while continuing
  to seek the public Money Tree purchase boundary.

R5 capture-enabled follow-up audit:
  User-run session `balatro-20260911T133440Z-db0b3f61` produced two complete
  ordinary production attempts before the bounded supervisor stopped. Attempt
  1 reached Ante 5 and attempt 2 reached the Ante 8 Violet Vessel; both ended
  with authoritative `GAME_OVER` loss checkpoints. Neither attempt purchased
  `v_money_tree`. Attempt 2 did buy Mercury, retain it into the next blind, and
  emit `USE_CONSUMABLE` at public run-log sequence 91, but neither the requested
  held-Planet directory nor the requested blind-start directory contains a
  private sidecar. The Mercury boundary and all blind starts therefore remain
  non-promotable; private usage/RNG authority must not be reconstructed from
  public post-state. After attempt 2, restart recovery failed closed because
  `G` could not be discovered; the generated crash report records that
  `Balatro.exe` was no longer running at failure-report time. That terminal
  condition supplies no evidence of a deterministic observer defect and is not
  repaired speculatively. The next live command must again pass both private
  capture directories, and their creation must be verified before treating a
  resulting public action as fixture evidence. Roadmap checkpoint commit
  `9701730dc9ffac19804f4f7b1cf68f5488ca5bfd` passed GitHub Actions run
  `34607815020`, job `103290494264`; the actual job log reports **2609 passed,
  1603 deselected in 118.23s**.

R5 private natural-capture boundary repair:
  User-run session `balatro-20260911T141029Z-68155427` completed all five
  bounded production attempts and stopped normally at the attempt limit. No
  attempt purchased `v_money_tree`. Attempts 2 and 3 emitted natural held
  Mercury and Uranus uses, respectively, while the enabled recorder failed
  closed before both actions because vanilla had initialized an exact empty
  `G.GAME.consumeable_usage` table but had not yet lazily created
  `consumeable_usage_total`. Vanilla creates that totals table on the first
  consumable use, so the canonical private-state decoder now admits only the
  empty-table/nil-totals combination as exact zero history; nonempty or other
  partial combinations still fail closed. The enabled blind-start recorder also
  failed before every action because the strengthened checkpoint tried to read
  the physical round draw pile at `BLIND_SELECT`. The canonical checkpoint now
  captures the public complete deck plus keyed RNG before the start and reads
  exact private physical order only at the post-deal `SELECTING_HAND` boundary;
  its failure diagnostic also retains the underlying private-reader reason.
  The incomplete Mercury/Uranus boundaries are not reconstructed or promoted.
  Focused capture validation passed with **50 passed**. Repair commit
  `c8c24ed71103a115e022f5c8c1b2277de3dd3804` passed GitHub Actions run
  `34612919619`, job `103307623061`; the actual job log reports **2612 passed,
  1603 deselected in 118.95s**. A new capture-enabled live batch is required to
  produce promotable held-Planet and post-deal draw-order evidence.

R5 post-action private-capture settlement repair:
  User-run session `balatro-20260911T150727Z-0b05509d` completed all five
  bounded production attempts and stopped normally at the attempt limit. No
  attempt purchased `v_money_tree`. Attempt 3 naturally bought and used Jupiter
  at public action sequence 81, but the enabled held-Planet recorder failed
  closed after the action because its public/private snapshot was still settling;
  the incomplete boundary is not reconstructed or promoted. All 28 enabled
  blind-start post-action captures failed closed because LuaJIT exposes the exact
  live physical draw pile as a one-based dense sequence while the private reader
  incorrectly required zero-based array indices. The canonical private draw-pile
  owner now validates exact contiguous keys `1..N`. The held-Planet recorder now
  uses a bounded two-consecutive-sample semantic stability window across both the
  public snapshot and private usage state; a settling state is admitted while
  continuous drift remains fail-closed. Focused affected validation passed with
  **55 passed**. Repair commit
  `613b4eacee4ca8c85b57b99a42d7948b7fe53048` passed GitHub Actions run
  `34616407289`, job `103319336941`; the actual job log reports **2613 passed,
  1603 deselected in 74.12s**. A new capture-enabled live batch is required for
  promotable held-Planet and strengthened blind-start evidence.

R5 natural held-Planet and strengthened blind-start fixture promotion:
  User-run session `balatro-20260911T153744Z-7b05a35c` completed all five
  bounded production attempts, stopped normally at the attempt limit, and lost
  at Antes 1, 3, 4, 4, and 5. No attempt purchased `v_money_tree`. Attempt 4
  naturally bought and used Uranus in `SELECTING_HAND`; the complete public rows
  and private usage sidecar are preserved with decompressed SHA-256 guards. Its
  first replay isolated one canonical mismatch: live re-admitted the consumed
  Uranus to the observed Planet generation pool while `use_planet_exact` left it
  suppressed. The exact owner now delegates re-admission to the existing ordered
  consumable-pool restoration owner when pool authority is observed, and the
  public evidence adapter admits only `SHOP` or `SELECTING_HAND` with the same
  phase on both sides. The unchanged natural fixture now passes public and
  private replay. The same batch produced ten complete blind-start sidecars;
  nine ordinary starts passed immediately. Attempt 1's first Small-Blind start
  is promoted as the strengthened natural fixture and proves the exact 44-card
  private post-deal draw order together with public and keyed-RNG parity.

  Attempt 5 also captured a natural `The Fish` start, but its replay exposed that
  the live-memory card normalizer omitted vanilla's exact `Card.facing` value.
  The canonical observer now publishes only exact `front`/`back` strings and
  leaves missing or malformed values unobserved. Because the captured Fish
  sidecar predates that repair, its missing facing authority is not reconstructed
  or promoted; a new natural Boss sidecar remains required. The remaining 31
  unsupported-Joker, four static-suit-Boss, and three active-Tag capture
  rejections remain intentionally fail-closed. Focused repair validation passed
  with **52 passed** and focused fixture validation passed with **35 passed**.
  Repair commit `e3054325d1b24abe74c9e0900de3f0d865488849` passed GitHub
  Actions run `34628704895`, job `103359991272`, with **2615 passed, 1602
  deselected in 120.21s**. Natural held-Planet commit `976e107a` and
  strengthened blind-start commit
  `1df499fc97b74610ab172f6f71745d512c5c2c4d` passed GitHub Actions run
  `34629346601`, job `103362092475`; the actual job log reports **2620 passed,
  1602 deselected in 121.40s**.

R5 current-HEAD GitHub Actions verification:
  Commit `d3cc63201e967e83124cd13dd0ba953c454e057c` passed GitHub Actions run
  `34556158163`. The actual `balatro-deterministic-tests` job log reports
  **2607 passed, 1603 deselected in 72.02s**. This supersedes the earlier
  current-status note about unavailable or failing CI evidence. The next task
  remains the genuinely live-only natural Money Tree capture; deterministic
  or post-state-inferred evidence is not a substitute.
  The roadmap synchronization commit `b5c30e48d998b86695e8a0473f9fd9d52e40024d`
  then passed GitHub Actions run `34594378030`; its actual job log reports the
  same **2607 passed, 1603 deselected**, in 122.00s.

R5 repository-only continuation verification:
  The pushed timeout-diagnostics commit remains synchronized at
  `2da940199e3a20cfb1ff9247b8f2cfcb76b27d23`. Focused bridge, supervisor,
  startup-handoff, crash-report, and failure-artifact regressions passed:
  17 passed, 0 failed, 0 skipped, 0 deselected. The authoritative R5 selector
  also passed: 2599 passed, 0 failed, 0 skipped, 1601 deselected. No newer
  repository artifact identifies a deterministic post-timeout defect, and no
  live Balatro process was launched or controlled during this verification.
  The next concrete failure remains live-only: the first-party bridge does not
  consume the STATUS command before the timeout budget; the still-pending
  command is cancelled and the diagnostic preserves command/path/response
  evidence. No natural Money Tree fixture, phase, checkpoint, or run log exists
  from that probe, so no gameplay conclusion is inferred. Continue with the
  independent R5 Economy-Transitions gate before requesting new live evidence.

R5 deterministic Economy-Transitions Tycoon parity:
  The existing canonical Voucher capability owner already supports the exact
  Tarot Tycoon and Planet Tycoon upgrades after their corresponding Merchant
  Voucher. The R5 public voucher-purchase parity suite now covers both
  transitions, preserving the observed money debit, prerequisite Voucher
  order, and exact 9.6 -> 32.0 rate upgrade. No production owner changed, and
  unsupported or malformed Voucher evidence remains fail-closed.
  Focused economy validation: 65 passed, 0 failed, 0 skipped, 0 deselected.
  Exact R5 selector: 2601 passed, 0 failed, 0 skipped, 1601 deselected.

R5 deterministic Economy-Transitions resource Voucher parity:
  The canonical `ShopTransitionEngine._apply_voucher_redemption_effects`
  resource owner was already exact; the uncovered R5 public parity slice was
  Crystal Ball, Grabber, Nacho Tong, Recyclomancy, Antimatter, and Palette.
  The focused regression now translates each public before/after mutation and
  replays it through `buy_voucher_with_public_evidence`, preserving the exact
  $10 debit, Voucher ownership order, and resource mutation. Wasteful and Paint
  Brush remain covered by the existing synthetic and real fixture regressions.
  No production owner changed, and private or unsupported Voucher evidence
  remains fail-closed.
  Focused voucher-purchase validation: 28 passed, 0 failed, 0 skipped,
  0 deselected.
  Exact R5 selector: 2607 passed, 0 failed, 0 skipped, 1601 deselected.
  The supported deterministic economy-transition mutations are now covered;
  the next gate is live-only natural-fixture evidence: capture and replay a
  real Money Tree economy-transition fixture now that the bridge and agent
  attach path are operational again.

R5 deterministic Economy-Transitions continuation verification from `0fa1390f`:
  Repository inspection found no additional supported deterministic Voucher
  purchase mutation after the resource, tycoon, Ante, pricing, reroll, shop
  size, edition-rate, and interest-cap families above. Omen Globe and Telescope
  remain explicitly admitted only for downstream pack-generation capability;
  they have no ordinary shop-purchase mutation and the public Voucher evidence
  owner correctly rejects them rather than inferring one. Focused Voucher and
  economy validation passed: 92 passed, 0 failed, 0 skipped; the requested
  shop-size redemption filename is absent because that coverage is owned by
  the existing shop-size transition tests. The exact R5 selector passed with
  2607 passed, 0 failed, 0 skipped, and 1601 deselected. No production owner
  changed. The next gate remains live-only natural-fixture evidence: capture
  and replay a new Money Tree fixture; no gameplay state is inferred until
  that evidence is recorded.
```

All counts above were read from the actual `balatro-deterministic-tests` job logs, not inferred from workflow status. The frozen strategic contract in `games/balatro/env_contract.py` contains no `PLANNED` entry; `BUY_CARD` and `REROLL_BOSS` remain explicitly unavailable and are excluded from `training_action_contracts()`.

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop generation: **BROADLY GREEN; REMAINING GAPS ARE SPECIFIC**.
- R3 typed strategic action vocabulary: **COMPLETE / GREEN**.
- R4 deterministic tactical bridge: **COMPLETE / GREEN FOR THE REQUIRED REPRESENTATIVE GATE**.
- R5 live/simulator parity harness: **CONDITIONALLY CLOSED FOR FORWARD DEVELOPMENT — THE NATURAL MONEY TREE FIXTURE IS EXPLICITLY ON HOLD, NOT PASSED**.
- R6 environment performance gate: **COMPLETE / GREEN**.
- Observation/action encoding: **COMPLETE / GREEN**.
- B0 RL baseline infrastructure: **IN PROGRESS — NEXT TASK IS THE RANDOM LEGAL STRATEGIC BASELINE**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **ON HOLD BY USER DIRECTION — DO NOT REQUEST MORE MONEY TREE RUNS UNTIL RESUMED**.

## Current strategic action contract

### SUPPORTED / training-exposed

```text
END_SHOP
REROLL_SHOP
BUY_JOKER          exact owned subset only
SELL_JOKER         audited inventory-only inverse lifecycle only
BUY_VOUCHER        exact owned subset only
BUY_CONSUMABLE     exact held-consumable purchase subset
OPEN_PACK          exact owned entry boundary
CHOOSE_PACK_OPTION exact admitted pack-option subset
SKIP_PACK          exact admitted pack-skip subset
USE_CONSUMABLE     exact held-Planet use subset
SKIP_BLIND         exact admitted Small-Blind/Tag subset
SELECT_BLIND       exact audited blind-start boundary
```

### UNAVAILABLE / never enters the training mask

```text
BUY_CARD
REROLL_BOSS
```

`BUY_CARD` is deliberately unavailable rather than planned: there is no dedicated canonical production `BUY_CARD` identifier and no frozen live shop legality/execution owner for Magic Trick / Illusion playing-card shop purchases. Do **not** invent an RL-only action to fill that gap.

`REROLL_BOSS` remains unavailable because no frozen canonical production action/owner exists for the current Red/White surface.

There is **no remaining PLANNED action in the frozen strategic contract**. If one appears later, it requires an explicit new canonical production capability, not a learner-side alias workaround.

---

# Foundation status

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
L3 environment freeze                COMPLETE
R0 headless environment architecture COMPLETE
R1 deterministic state/acquisition   SUBSTANTIALLY COMPLETE
R2 RNG/lifecycle/shop generation     BROADLY GREEN / SPECIFIC GAPS REMAIN
R3 typed action vocabulary           COMPLETE / GREEN
R4 deterministic tactical bridge     COMPLETE / GREEN
R5 live/simulator parity harness      CONDITIONAL CLOSE / MONEY TREE ON HOLD
R6 environment performance gate      COMPLETE / GREEN
O observation/action encoding        COMPLETE / GREEN
B0 RL baseline infrastructure        IN PROGRESS
PPO strategic learner                NOT STARTED
```

The simulator is authoritative only for the promoted representative R5 surface.
The natural Money Tree transition remains unpromoted and must not be treated as
live-validated while its capture gate is on hold.

---

# Historical roadmap retention

The older roadmap contained more phases because it documented the symbolic/Bond competence path in implementation detail. Those phases were intentionally closed or superseded before the deterministic-environment/RL path began. They remain historical contracts and evidence; they are not active work and must not be silently reopened.

| Earlier phase family | Current status | What remains binding |
|---|---|---|
| A–K symbolic mechanics and Bond integration | **COMPLETE** | Exact mechanics, legality, public-state boundaries, canonical tactical owners, candidate projection, deterministic regressions, and useful Bond-derived features |
| L live stabilization and defect repair | **COMPLETE** | Classify a demonstrated failure before patching; repair the first wrong canonical owner; add a focused regression; use live runs only for hypotheses that require Balatro |
| L3 environment freeze | **COMPLETE** | Preserve the frozen production/environment boundary and fail closed when exact behavior is not owned |
| Manual Bond coefficient tuning | **RETIRED AS PRIMARY PATH** | Existing Bond signals may become observations/features, but manual coefficients do not replace the learned strategic policy |
| Higher-stake and additional-deck progression | **DEFERRED** | Begin only after Red Deck / White Stake competence passes the final learned-policy evaluation gate |

## Retained engineering invariants

1. **First wrong layer owns the defect.** Fix mechanics, state, RNG, projection, legality, consumer valuation, action arbitration, runtime, or telemetry at the earliest incorrect canonical boundary. Never compensate with a later rescue wrapper.
2. **Counterfactual influence must reach the final action.** For deterministic proofs, hold public state, legal actions, and unrelated evidence constant; change the relevant fact and prove that the final action changes when it should.
3. **Representative paths require end-to-end proof.** Unit correctness is insufficient when state acquisition, transition, mask, serialization/replay, tactical execution, or live dispatch can still disagree.
4. **Live batches are hypothesis-driven.** A loss is evidence to inspect, not proof of a defect. Do not run repeated open-ended Balatro batches merely to search for something to change.
5. **Run-level diagnosis remains connected.**

```text
early survival
→ first scoring engine
→ economy stabilization
→ scalable engine
→ boss-safe execution
```

6. **Evaluation must compare against frozen baselines.** The old minimum of 20 completed episodes per arm applied to manual live tuning; it is not automatically sufficient for RL. B0/PPO must define seeded and unseeded evaluation sets, sample size/power, promotion metrics, and regression/pathology gates before learned-policy promotion.
7. **CI validates the roadmap; it does not authoritatively rewrite development history.** Completed phases may be compressed only when their status, retained outputs, and superseded boundaries remain recorded here or in linked archival documents.

## Explicitly superseded concepts

Do not restore the old persistent strategy controller, named strategy identity as action authority, FORMING/PINNED states, `StrategyPlan`, goal/prescription plumbing, generic pivot FSM/resistance, one execution tree per Bond, post-owner rescue authority, or manual Bond tuning as the primary competence path.

The active development sequence is now:

```text
R5 live/simulator parity
→ R6 performance
→ O observation/action encoding
→ B0 baselines
→ PPO
→ controlled Red/White promotion
→ higher stakes/decks
```

---

# R1 — deterministic state/acquisition

## Owned

- Red Deck / White Stake canonical state validation.
- Strict public/private card-zone ownership.
- Permanent owned-deck truth from `G.playing_cards` with all-or-nothing LuaJIT/TValue decoding.
- Next-round hand/discard allowances where required.
- Exact resource-sensitive Joker acquisition effects for the admitted group.
- Broad static score/rule/retrigger Joker acquisition groups whose acquisition is inventory-only.
- Owned-deck-dependent scoring Jokers only when permanent deck state is authoritative.
- Exact supported Voucher acquisition effects listed below.
- Fail-closed malformed/noninteger prices.
- Exact audited Joker sale subset whose inverse lifecycle is inventory-only.

## Exact Joker acquisition families retained

The inventory-only/scoring-safe surface includes the previously audited static, hand-rule, hand-shape, suit, retrigger, money, and conditional scorers.

Resource-sensitive exact acquisitions include:

```text
Juggler
Stuntman
Drunkard
Troubadour
Merry Andy
```

Owned-deck-dependent scoring acquisitions include:

```text
Driver's License
Erosion
Steel Joker
Stone Joker
```

only when permanent deck state is authoritative.

Burglar's blind-selection consequence is now owned on the admitted exact `SELECT_BLIND` lifecycle path. Acquisition/sale legality must still be proven at their own boundaries rather than inferred merely from lifecycle support.

## Still fail closed

- unknown/unaudited Joker acquisitions;
- Joker editions whose acquisition changes capacity semantics, especially Negative;
- Joker sale/inverse lifecycle cases not in the audited exact sale subset;
- unsupported playing-card shop mechanics;
- unsupported Voucher mechanics listed below.

Representative historical gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

---

# Exact currently supported Voucher families

## Resource / capacity

```text
v_crystal_ball
v_grabber
v_nacho_tong
v_wasteful
v_recyclomancy
v_antimatter
v_paint_brush
v_palette
```

## Joker edition rate

```text
v_hone
v_glow_up
```

## Shop discount

```text
v_clearance_sale
v_liquidation
```

## Shop type rate

```text
v_tarot_merchant
v_tarot_tycoon
v_planet_merchant
v_planet_tycoon
```

## Persistent reroll cost

```text
v_reroll_surplus
v_reroll_glut
```

## Interest cap

```text
v_seed_money
v_money_tree
```

## Main-shop size

```text
v_overstock_norm
v_overstock_plus
```

## Ante / round allowance

```text
v_hieroglyph
v_petroglyph
```

`games/balatro/env/voucher_capabilities.py` is the canonical per-boundary capability owner. Exact generation capability is distinct from exact redemption/cash-out capability; never replace these checks with a blanket `if state.vouchers` rule.

### Canonical upgrade progression

```text
Glow Up         requires Hone
Liquidation     requires Clearance Sale
Tarot Tycoon    requires Tarot Merchant
Planet Tycoon   requires Planet Merchant
Reroll Glut     requires Reroll Surplus
Money Tree      requires Seed Money
Overstock Plus  requires Overstock
Petroglyph      requires Hieroglyph
```

Voucher ownership remains an ordered list because redemption order is observable/replay-relevant. Membership/prerequisite checks may be set-like, but transitions append in canonical redemption order and never normalize the list into a set.

### Hieroglyph / Petroglyph

Pinned vanilla redemption:

```text
both:
  ease_ante(-1)
  round_resets.blind_ante -= 1

Hieroglyph:
  round_resets.hands -= 1
  current hands_left -= 1

Petroglyph:
  requires Hieroglyph
  round_resets.discards -= 1
  current discards_left -= 1
```

Canonical ownership:

```text
HeadlessRunState.blind_progression_state
        ↓
ante_voucher_redemption.py
        ↓
ShopTransitionEngine legal mask + BUY_VOUCHER execution
```

The path fails closed when retained progression is absent/stale, the required current/persistent allowance is unobserved or irreducible, price is malformed/unaffordable, or Petroglyph lacks Hieroglyph. Successful redemption consumes no RNG and atomically updates public and private state.

### Boundary-limited or unsupported Voucher centers

```text
v_omen_globe      base-shop generation / paid-reroll zero-effect boundary only
v_telescope       base-shop generation / paid-reroll zero-effect boundary only
v_observatory
v_blank
v_magic_trick
v_illusion
v_directors_cut
v_retcon
```

Blocked by real mechanics:

- Omen Globe: Spectral generation inside Arcana packs.
- Telescope / Observatory: Celestial pack/Planet lifecycle and Observatory held-Planet scoring.
- Blank: progression/unlock semantics rather than an ordinary immediate gameplay modifier.
- Magic Trick / Illusion: exact playing-card shop generation/purchase/modifier generation; `BUY_CARD` is unavailable in the frozen action contract.
- Director's Cut / Retcon: exact Boss-reroll action/state ownership; `REROLL_BOSS` is unavailable in the frozen action contract.

Do not promote these through a blanket allowlist.

---

# R2 — RNG + lifecycle + shop/pack generation

## RNG / shuffle / ordering — GREEN

```text
33791671797  1432 passed, 1594 deselected   exact LuaJIT/Balatro RNG
33791916289  1435 passed, 1594 deselected   exact pseudoshuffle
33795507133  1461 passed, 1594 deselected   env_r2/card order
```

Owned:

- keyed Balatro pseudoseed progression;
- LuaJIT combined Tausworthe draws;
- bit-preserving RNG snapshot/restore;
- vanilla pseudoshuffle semantics;
- private playing-card creation order / physical deck order where provable;
- private Joker order where lifecycle parity requires it.

## Round/blind/Boss lifecycle — BROADLY GREEN

The environment owns audited Red/White blind start, draw, resource modification, Boss active effects, disable/defeat restoration, and round resolution across all 28 vanilla Bosses. Hidden-information behavior remains masked correctly.

Owned lifecycle details include:

- normal and pre-Ante blind progression;
- literal nonpositive Ante handling where vanilla permits it;
- exact base blind requirements for the modeled Red/White Ante range;
- Boss selection/activation/disable/defeat restoration;
- audited `setting_blind` lifecycle effects;
- exact physical shuffle/deal with hidden draw order retained privately;
- round-end cashout and ordinary next-blind/Ante transitions;
- exact admitted blind-skip progression/Tag behavior;
- canonical skip counter ownership where admitted.

Representative gates:

```text
33796012173  1467 passed, 1594 deselected
33855720629  1734 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
33915588784  1924 passed, 1595 deselected
33965599236  2233 passed, 1595 deselected
33966224227  2239 passed, 1595 deselected
33967536736  2257 passed, 1595 deselected
33971114617  2278 passed, 1595 deselected   SELECT_BLIND exposure guard closure
33975435937  2279 passed, 1595 deselected   retained blind skip tag prerequisite
33978049029  2320 passed, 1595 deselected   latest verified pre-R3-closure head
```

## Normal shop / Voucher / pack generation — GREEN FOR OWNED PATHS

Owned slices include:

- normal main-shop slot type polling;
- ordinary Joker rarity/center/edition generation for authoritative catalogues;
- Tarot/Planet normal generation;
- variable supported main-shop capacity;
- paid shop reroll at current exact capacity;
- centralized `Card:set_cost`-compatible pricing;
- generated visible-shop repricing from immutable base metadata;
- Voucher eligibility/identity polling;
- Voucher runtime metadata + exact price;
- separate normal Voucher slot publication;
- supported Voucher state through shop generation and ordinary cash-out;
- all supported Voucher effects consumed by canonical downstream owners;
- exact admitted Buffoon option ordering/choice/skip behavior;
- exact admitted held-Planet use behavior and guards;
- exact audited Joker sale path.

Representative later gates:

```text
33956949501  2133 passed, 1595 deselected   Hone / Glow Up
33959454017  2155 passed, 1595 deselected   discount pricing
33960365203  2165 passed, 1595 deselected   discount redemption
33961839253  2208 passed, 1595 deselected   reroll Voucher lifecycle
33962480568  2209 passed, 1595 deselected   Voucher-preserving cashout
33964693188  2224 passed, 1595 deselected   interest-cap + Overstock closure
33965599236  2233 passed, 1595 deselected   Hieroglyph/Petroglyph downstream audit
33967536736  2257 passed, 1595 deselected   Hieroglyph/Petroglyph canonical purchase
33978049029  2320 passed, 1595 deselected   pack/sale/Planet-use era latest verified head
```

### Headless `ROUND_EVAL` boundary

The project deliberately uses `ROUND_EVAL` as the headless pre-cashout boundary consumed by `cash_out_baseline_ordinary_blind()`. This name is not a claim that the card-zone timing is identical to vanilla's internal state label.

For the exact admitted lifecycle:

- a completed Play has already moved its selected cards from hand → play → discard and left `played_pile` empty;
- a cleared blind may still retain unplayed held cards in `public.hand` at this headless boundary;
- `round_end.py` / `repopulate_round_end_deck()` owns the admitted clear-path hand/discard → deck repopulation before payout/shop progression;
- final-hand failure enters `GAME_OVER` and does not execute clear-path repopulation.

Do not duplicate this repopulation inside the tactical Play owner merely to mirror vanilla's internal state-label timing.

---

# Fail-closed rule

If exactness cannot be proved:

- reject the transition/action;
- omit it from the training mask;
- retain `None`/unobserved state where applicable;
- do not silently substitute related state;
- do not invent hidden/public state merely for simulator convenience.

Examples already enforced:

- partial LuaJIT/TValue permanent-deck reads invalidate `owned_deck`;
- future draw order remains private;
- Amber Acorn hidden Joker mapping is masked while active;
- unsupported Joker inverse sale lifecycles remain rejected;
- pre-deal Manacle/Chicot requires authoritative retained physical deck order;
- malformed Joker/Tarot/Planet/Voucher catalogues reject all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal;
- shop generation preflights dependencies before first type RNG;
- Voucher selection never falls back to a guessed/static Python catalogue;
- unsupported Voucher centers never become legal merely because identity/price/slot are known;
- duplicate, malformed, or unobserved nonempty Voucher ownership is rejected;
- Voucher upgrade ownership/state mismatches are rejected rather than repaired by inference;
- ordinary cash-out rejects unsupported Voucher generation/pricing/economy state rather than erasing it;
- Ante Voucher redemption rejects stale/missing private `blind_ante` ownership;
- Ante Voucher redemption rejects unobserved or irreducible current/persistent allowances;
- unsupported Tag outcomes stay masked rather than producing phantom post-skip states;
- unsupported pack option/skip/use paths stay masked;
- `BUY_CARD` and `REROLL_BOSS` are explicit unavailable capabilities rather than phantom learner actions;
- tests must mark authoritative empty/zero observations explicitly instead of relying on defaults.

---

# R3 — typed strategic action vocabulary — COMPLETE / GREEN

Every training-visible action requires:

1. canonical production action identifier;
2. frozen legality owner;
3. exact headless transition owner;
4. deterministic serialization/replay representation;
5. mask representation;
6. focused live/simulator parity fixture before the simulator becomes training truth.

## Supported / frozen

```text
END_SHOP
REROLL_SHOP
BUY_JOKER
SELL_JOKER
BUY_VOUCHER
BUY_CONSUMABLE
OPEN_PACK
CHOOSE_PACK_OPTION
SKIP_PACK
USE_CONSUMABLE
SKIP_BLIND
SELECT_BLIND
```

Each name above is an RL-facing alias over a canonical production identifier; it does not create a second action system. Each action remains narrow at runtime: only exact state/item/tag/pack/consumable subsets enter the legal mask.

## Explicitly unavailable

```text
BUY_CARD
REROLL_BOSS
```

`BUY_CARD` closure commits:

```text
1e6eca9  refactor(balatro): close unavailable card shop action
3a43797  test(balatro): freeze unavailable card shop capability
```

Reason: no dedicated canonical production identifier or live shop legality/execution owner exists. Magic Trick/Illusion playing-card shop support is a future mechanics expansion, not a missing R3 alias.

`REROLL_BOSS` remains unavailable for the same canonical-ownership reason.

## R3 closure proof

- `games/balatro/env_contract.py` contains no `PLANNED` contract in the frozen action surface.
- `BUY_CARD` and `REROLL_BOSS` remain outside `training_action_contracts()`.
- GitHub Actions run `33982517717` at `2e8daa4b64694cc22862f99ea16adea3c61c00f2` completed with **2331 passed, 1595 deselected**.
- R4 then advanced on top of this green gate without reopening the R3 vocabulary.

Do not reopen a supported R3 action without a concrete regression.

---

# R4 — deterministic tactical bridge — COMPLETE / GREEN

## Goal

RL controls strategic run-development boundaries while existing deterministic hand-level owners continue to choose exact play/discard actions. **Do not rewrite the tactical engine inside the learner or create a second scoring/hand-selection implementation.**

## Canonical tactical audit — retained findings

1. Canonical tactical payloads are `BalatroAction(PLAY_CARDS, cards=[...])` and `BalatroAction(DISCARD_CARDS, cards=[...])` from `games/balatro/actions.py`; selected cards are canonical public hand objects, not an RL-only index action type.
2. The production call chain is `StrategyAwareLiveMemoryInjectedSingleStepRunner` → `_recommend_hand_with_bonds()` → `PathAwareLiveHandActionDecisionEngine(policy=StrategyAwareLiveHandActionPolicy(...))` → `.decide(state)` → `HandActionDecision.action`. The headless bridge calls that same production-shaped `decide(state)` boundary and accepts only the canonical `BalatroAction` carried by `decision.action`; the former test-only `.plan(state)` shape is rejected rather than retained as a compatibility layer.
3. `D1LiveBlindClearPlanner` in `games/balatro/live/hand_action_planner.py` extends the core planner in `hand_action_planner_core.py`, obtains Play/Discard candidates from the shared generator, and filters Play candidates through `boss_play_action_is_legal`; Boss-aware score projection remains in the shared live evaluator path.
4. Runner / To Do List target-hand evidence is owned by `games/balatro/target_hand_engine_policy.py` and consumed inside canonical D1 ranking; R4 does not duplicate that heuristic.
5. `games/balatro/env/public_observation.py` is the policy-visible sanitization boundary. Private physical draw order remains on `HeadlessRunState` and is never passed to the tactical decision engine.
6. The frozen strategic action contract remains `games/balatro/env_contract.py`; there is no separate tactical learner action surface.
7. `games/balatro/env/play_transition.py` owns the narrow exact ordinary Small/Big-blind action-time lifecycle and now composes the admitted exact Boss `press_play` mutations at the canonical source-order position.
8. `games/balatro/env/tactical_transition.py` composes admitted Discard and Play owners behind the production `.decide()` boundary. Unsupported tactical states still fail closed.
9. Representative exact Boss tactical Play is admitted for **The Tooth** and **The Hook** only where their complete action-time lifecycle is owned. Other Bosses remain fail closed unless their full relevant behavior is exact.
10. `games/balatro/env/tactical_evidence.py` persists policy-visible pre/action/post evidence with selected visible hand indices while excluding simulator-private draw order, RNG, hidden identities, and local object identity. Durable snapshots are frozen so later simulator mutation cannot rewrite earlier trajectory evidence.

## Admitted R4 slice — green

```text
headless SELECTING_HAND
        ↓
policy-safe public observation
        ↓
production-shaped decision_engine.decide(state)
        ↓
HandActionDecision.action / canonical BalatroAction
        ↓
canonical PLAY_CARDS or DISCARD_CARDS
        ↓
visible-position mapping / exact action owner
        ↓
headless transition
        ↓
public tactical trajectory evidence
```

Exact admitted behavior:

- selected cards are validated as 1–5 distinct visible positions and resolved in current hand-area order;
- private/public draw and discard zones must agree before mutation;
- permanent playing-card order must remain authoritative;
- the input run is copy-on-write;
- Discard moves selected cards to the exact discard tail, updates `discards_remaining` / `discards_used`, and redraws from retained private physical order;
- ordinary Play decrements hands before movement, moves hand → play → discard, records played-this-ante history, evaluates the canonical poker hand and deterministic score, updates score/hand counters/visibility/last hand, and resolves clear vs continue/redraw vs final-hand loss;
- admitted Tooth and Hook Play effects compose through canonical Boss ownership/source order;
- policy input is `public_observation_state(run.public)`, so face-down identity remains masked;
- decision-selected foreign card objects fail closed;
- the legacy test-only `.plan(state)` shape fails closed rather than being supported in parallel;
- unsupported Joker/card callbacks, random scoring effects, unowned Boss effects, and unsupported decision actions fail closed.

## R4 closure proof

```text
c117ab054e8cebb8a402711cca46ed48fb076172
  feat(balatro): bridge public tactical discard

5d8565b6910eb9c77b8342465dc404bd6a902840
  refactor(balatro): wire R4 tactical decision engine

652b32624ae2feaad9e768baac9f505b386bb271
  feat(balatro): own ordinary R4 play lifecycle

98ab566071f0af94305ffaba5b9fa0482e25b4ad
  feat(balatro): admit exact Tooth tactical play

f8bc7aabafcd766fd9bcada15e8bef489977d7a5
  feat(balatro): admit exact Hook tactical play

e9408fa943bbc2609f3ee96e53318ba2ff2c874c
  feat(balatro): record public tactical trajectory evidence

0603f420ee7f7d1f235c21b0ea9debc7b72442e5
  fix(balatro): freeze tactical evidence snapshots
```

The required R4 exit gate is representative ordinary + Boss tactical correctness and R5-safe trajectory evidence, not exhaustive admission of all 28 Boss Play paths. Unsupported Boss tactical paths remain intentionally excluded rather than blocking R4 closure.

## R4 exit criteria — SATISFIED

- deterministic tactical owner callable from headless `SELECTING_HAND` states;
- exact play/discard legality shared with canonical mechanics;
- tactical action transitions return to the correct next owner/state;
- representative ordinary + Boss tactical regressions green;
- no hidden-information leakage;
- no second tactical strategy implementation;
- tactical trajectory metadata sufficient for R5 comparison.

Do not reopen R4 solely to increase Boss coverage. Reopen only for a concrete R5 parity defect or a separately scoped mechanics expansion.

---

# R5 — live/simulator parity harness — IN PROGRESS

Required before treating the simulator as authoritative training truth.

## Completed infrastructure — green

- `PublicTacticalTransitionEvidence` is the canonical public tactical pre/action/post evidence type; no second tactical action schema exists.
- `games/balatro/env/parity.py` canonicalizes policy-visible state while removing engine-local identity fields.
- single-transition tactical comparison reports differences in `before`, `action.name`, `action.selected_hand_indices`, and `after`.
- `games/balatro/live/parity_capture.py` converts successful durable live run-log observation/decision/action-result rows into canonical tactical evidence and rejects malformed or mismatched tactical records rather than repairing them heuristically.
- ordered tactical trajectory comparison treats transition count and order as evidence; it never truncates one side to manufacture a match.
- durable live-log rows can now be compared directly against an ordered simulator evidence trajectory through the same canonical comparator.
- `PublicStrategicTransitionEvidence` is the canonical public strategic pre/action/post record and reuses the frozen R3 `EnvAction` vocabulary rather than inventing a second strategic action schema.
- successful supported live `BUY_JOKER` run-log transitions map the combined live shop `area_index` to the exact translated Joker slot and fail closed when the target cannot identify exactly one supported translated Joker.
- the supported `BUY_JOKER` regression now rebuilds `HeadlessRunState` directly from the translated live-before state, executes `ShopTransitionEngine` through `buy_joker_with_public_evidence`, and compares the resulting strategic evidence without copying/normalizing live before/after state into the simulator side.
- `games/balatro/live/joker_purchase_fixture.py` provides an offline opt-in preservation seam that selects one coherent settled `BUY_JOKER` boundary from the canonical public run log and writes the original `balatro-run-experience-v1` observation/decision/action-result rows unchanged; it creates no production-side action/evidence schema.
- exact integral live Joker price metadata is canonicalized at `LiveJokerFactory`, aligning Lua numeric values such as `4.0` with the headless integer-price contract while leaving non-integral prices fail-closed.
- successful supported live `BUY_VOUCHER` run-log transitions now reuse the same targeted-purchase action mapping and `PublicStrategicTransitionEvidence` path, mapping live combined-shop `area_index` to the translated Voucher slot and rejecting unsupported centers or mismatched identities.
- `games/balatro/live/voucher_purchase_fixture.py` reuses the generic purchase-fixture seam and preserves one coherent successful `BUY_VOUCHER` observation/decision/action-result boundary without inventing Voucher-specific production truth.
- translated live shop items expose their authoritative center identity through the canonical `center_key` interface expected by exact headless Voucher mechanics while retaining `center` for live-target structural comparison.
- the first real supported Voucher fixture is preserved byte-for-byte after decompression with a SHA-256 guard and replays unchanged through the canonical headless Voucher owner.
- live permanent playing-card identity now retains only exact observed `live_id` values: integral Lua numbers normalize to integers; missing identity remains missing; invalid/partial identity never falls back to public array position. This lets headless permanent creation order be derived from authoritative IDs without exposing future physical draw order.
- structurally untouched complete base decks remain exact when those cards carry authoritative live IDs; the canonical deal owner now treats the IDs as creation-order evidence rather than as a deck modification.
- `games/balatro/live/blind_start_parity_checkpoint.py` captures stable public state, keyed-RNG replay authority, and active-Tag count; it restores the complete deck by exact permanent IDs, delegates to `select_blind_exact`, compares public evidence separately from private post-action RNG, and fails closed on drift, active Tags, or mismatched card identity.
- `games/balatro/live/reroll_parity_checkpoint.py` captures coherent complete-SHOP public state plus exact private RNG/reroll replay authority and rejects active Tags, free rerolls, unobserved Voucher state, or unstable checkpoints rather than normalizing them away.
- exact ordinary paid `REROLL_SHOP` can be rebuilt from a private checkpoint and replayed through the canonical headless reroll owner; the comparator checks public transition evidence, previous/next reroll cost, and post-action RNG snapshot.
- `games/balatro/live/reroll_parity_capture.py` persists this private replay authority in an opt-in per-run sidecar. The normal durable run-experience JSONL remains public-only.
- the production live entry exposes `--reroll-parity-directory`. Capture failures and replay mismatches are diagnostic/observational only: they cannot suppress, rewrite, or falsely relabel a successfully settled production action.
- parameterless live `SKIP_BLIND` rows now map to the frozen R3 action and the
  exact Small-Blind/Economy-Tag headless owner. The opt-in private checkpoint
  retains Small/Big/Boss statuses, `blind_on_deck`, `blind_ante`, both generated
  Tag identities, active-Tag count, and the run skip counter. It captures no RNG
  because this admitted transition consumes none. Unsupported Tags, pre-existing
  active Tags, missing progression facts, and Big-to-Boss skips remain fail-closed.
- settled final `BUFFOON_PACK` `SELECT_PACK_CARD` and `SKIP_BOOSTER` rows now map
  to the frozen `CHOOSE_PACK_OPTION` / `SKIP_PACK` aliases through the shared
  public strategic evidence path. Selection requires an exact nonnegative area
  index and visible identity; targeted hand-card selections, malformed skips,
  failed results, and nonterminal pack transitions fail closed. The evidence
  wrappers delegate directly to the existing exact R3 pack owners.
- `games/balatro/live/buffoon_pack_parity_capture.py` owns the opt-in private
  pre-action checkpoint: one stable complete Buffoon snapshot, exact
  `G.GAME.pack_choices == 1`, ordered visible Joker records, and
  `G.GAME.PACK_INTERRUPT` resolved through Balatro's own `G.STATES`. It strips
  UI geometry, preserves exact live identity, admits no unsupported Joker,
  edition, multi-pick, capacity-blocked choice, or inexact return origin, and
  replays through the canonical R3 pack owners without inventing RNG authority.
- `--buffoon-pack-parity-directory` is forwarded through the sole canonical
  `BalatroAgentToggle.bat --attempt N` path. Capture/replay failures are
  diagnostic only and cannot suppress or rewrite a settled gameplay action.
- the first natural supported Buffoon fixture is preserved with decompressed
  SHA-256 guards for both its unchanged public transition rows and private
  sidecar. It exposed one concrete canonical-owner mismatch: live temporarily
  removes every visible Buffoon option from `used_jokers`, then re-admits the
  unchosen option when the pack closes. `choose_pack_option_exact` now delegates
  that restoration to the existing generation-pool owner while leaving the
  acquired Joker suppressed. The unchanged fixture passes both public and
  private replay.
- settled held-Planet `USE_CONSUMABLE` rows now map an exact visible area index
  and name to one translated `PlanetCard`, reuse the frozen R3 action vocabulary,
  and compare through shared public strategic evidence. Replay delegates to
  `use_planet_exact`; targeted-card consumables, Tarot/Spectral use, non-SHOP
  transitions, ambiguous identity, failed results, and missing private usage
  history remain fail-closed.
- successful active-main-shop `SELL_JOKER` rows now retain the exact owned
  `joker_index`, map through the frozen R3 action vocabulary, and compare on the
  shared public strategic evidence path. Replay delegates directly to
  `sell_joker_exact`; unsupported inverse lifecycles, Eternal or editioned
  Jokers, malformed/ambiguous indices, failed results, and non-SHOP boundaries
  fail closed. Joker sale consumes no RNG, so this slice adds no private replay
  schema.
- the first passing real Small-Blind fixture now also serves as the owned-deck
  composition parity gate: the translated `owned_deck` contains exactly 52
  authoritative integral live IDs and exactly one copy of every Red Deck base
  rank/suit identity. The public fixture keeps permanent composition separate
  from any hidden physical draw order; no simulator-side reconstruction of
  permanent truth from `G.deck.cards` was added.
- the frozen R3 action surface currently has no supported playing-card acquisition
  or deterministic conversion action that mutates permanent composition end to
  end. `BUY_CARD` remains unavailable, Tarot/Spectral conversion remains outside
  the admitted `USE_CONSUMABLE` Planet slice, and R4 tactical Play intentionally
  fails closed before unsupported destruction callbacks. The existing canonical
  destruction owner is retained for future exact expansion rather than being
  promoted through a synthetic parity action.

Green checkpoints:

```text
7dd4f36341fd5624d05db2e7b59e808f81ceb5cd
  feat(balatro): add R5 tactical parity comparator

da7e4e9605d37584b116f28274bdb7fc91ac728a
  feat(balatro): adapt live run logs for R5 parity
GitHub Actions run 34005381429
GitHub Actions job 101411468974
2373 passed, 1595 deselected

0a657d961b13bac12371466418ff470c15e62a61
  feat(balatro): compare R5 tactical trajectories
GitHub Actions run 34005877151
GitHub Actions job 101412827495
2377 passed, 1595 deselected

e116bf09e0c13c6092dc57b7bc2dae5e7f9ee792
  feat(balatro): replay exact R5 shop reroll parity
GitHub Actions run 34022177202
GitHub Actions job 101456639275
2401 passed, 1595 deselected

b15fab5fe2bec0080c383a009dbef4f00cc89e12
  feat(balatro): capture live R5 reroll parity
GitHub Actions run 34024889806
GitHub Actions job 101463994146
2409 passed, 1595 deselected

99a4776ce8d01b47fb0a460cdc31d5ea63558b2e
  test(balatro): cover Telescope paid reroll parity state
GitHub Actions run 34213635015
GitHub Actions job 102020161503
2419 passed, 1595 deselected

606c7b4535176e92f9bc87192cc9a049670a0d6e
  fix(balatro): align paid reroll with live parity
9fbfe70386e3141c565cd07c655decd5194dd1cb3
  test(balatro): align exact reroll regressions
GitHub Actions run 34217561085
GitHub Actions job 102032815831
2421 passed, 1595 deselected

7b1fb06f7a307a2ac2d0fec8613f18c6eaeeb79d
  fix(balatro): restore branch tree after launcher update
GitHub Actions run 34218019368
GitHub Actions job 102034289630
2427 passed, 1595 deselected

256d56baf36f0d5a32b9aabf827cbbdc2643c3f5
  feat(balatro): add Joker purchase parity evidence
adfa8458fbee9f6b51db0f7b8b25e8ab36d0c56c
  test(balatro): seed R5 joker purchase replay
0183d09d729dad15f72948be0326a10432ecea07
  test(balatro): complete R5 joker purchase fixture metadata
30b8ca49678f1826b92d8939d9337997d5275dbc
  test(balatro): replay R5 Joker purchase without normalization
8d6b64adc3ab2884d59e5d59a9d2a8f448f83ed5
  test(balatro): compare R5 purchase identity structurally
GitHub Actions run 34222351675
GitHub Actions job 102048209359
2431 passed, 1595 deselected

e2e4c23ea669283fc3991cc5bf6ad10920a22f9b
  test(balatro): replay real R5 Joker purchase fixture
6b93714d3ca496d6440be75f3b169e5b48b04cd3
  fix(balatro): normalize exact live Joker prices
a709b9c74e688f20ebaa82ba8fed5e02d2e231fa
  test(balatro): freeze exact live Joker price translation
GitHub Actions run 34229665010
GitHub Actions job 102072335608
2437 passed, 1595 deselected

36bbe5eb2f7057bb41d4846996c8efca9b466811
  fix(balatro): normalize live shop center identity
GitHub Actions run 34234881414
GitHub Actions job 102089904106
2443 passed, 1595 deselected

4aba3b42f40f03b1d35dc58414d913e62537b369
  fix(balatro): preserve real Voucher fixture bytes
GitHub Actions run 34237730786
GitHub Actions job 102099701468
2445 passed, 1595 deselected

9af3cc3691b75b4aac178265124927537542630e
  fix(balatro): normalize exact playing-card live ids
2c2d96055b84a8791fafe53372446bbc25e54314
  test(balatro): freeze exact playing-card live ids
92d2a2abc6301c32fef2927c11eb76a3e6e2dd74
  test(balatro): select exact playing-card id regressions
GitHub Actions run 34250416208
GitHub Actions job 102143121535
2452 passed, 1595 deselected
```

The first real paid-reroll fixture,
`balatro-20260908T091943Z-e7a1ad15-attempt-001`, contains two settled
`REFRESH_SHOP` transitions. Its original verdicts exposed exact canonical
defects: the Joker pool seed omitted Ante, White Stake failed to consume the
unconditional `etperpoll{ante}` draw, visible Joker pool lifecycle was not
restored/suppressed across reroll, Planet shop pricing was doubled contrary to
pinned vanilla, live shop cards did not retain exact base cost, and parity
compared engine-local item classes instead of public shop identity/price.
Those owners were repaired at `606c7b45` and their exact regressions aligned at
`9fbfe703`. Replaying the unchanged two-row fixture now yields
`comparison.matches == true` for both transitions, including public state,
reroll-cost state, and post-action RNG.

Post-capture readiness repairs now own depleted-shop rerolls, exact Tarot/Planet
duplicate-suppression pool lifecycle, production publication of authoritative
consumable-generation catalogues, surfaced replay rejection causes, and explicit
Omen Globe/Telescope zero-effect capability at the ordinary base-shop/paid-reroll
boundary. These repairs do not constitute a live parity fixture.

The first real ordinary Joker-purchase fixture is repository-preserved from
`balatro-20260831T082151Z-78326f05-attempt-001`, sequences 47–49. It is the
original canonical public observation/decision/action-result boundary for buying
Juggler at combined shop `area_index=1`. The unchanged fixture rebuilds a
headless SHOP state, resolves canonical Joker slot 1, spends money 14 → 10,
moves Juggler from the shop into owned Jokers, leaves Crafty Joker in the shop,
and applies Juggler's exact acquisition effect `hand_size: 8 → 9`. Its first CI
replay exposed a translation inconsistency: Lua-extracted exact prices arrived as
numeric `4.0` while the headless contract correctly requires exact integer shop
prices. `LiveJokerFactory` now canonicalizes only integral numeric price metadata;
non-integral values remain unsupported rather than rounded. The unchanged real
fixture then passed canonical strategic parity at `a709b9c7`.

The first real supported Voucher-purchase fixture is repository-preserved from
`balatro-20260908T135908Z-3f93a77a-attempt-001`, sequences 59–61. It is the
unchanged canonical public observation/decision/action-result boundary for
buying Paint Brush (`v_paint_brush`) at combined shop `area_index=0`. The live
boundary spends money 18 → 8, removes Paint Brush from the shop, appends
`v_paint_brush` to ordered Voucher ownership, and changes public hand size 8 → 9.
The first deterministic replay exposed the actual canonical integration defect:
translated `LiveShopItem` identity was published as `center`, while the exact
headless Voucher owner reads canonical `center_key`. The live shop-item model now
normalizes that same authoritative center identity at its canonical interface;
there is no Voucher-only legality bypass. The real fixture is stored compressed
but its exact decompressed original rows are guarded by SHA-256
`36d25e575079e279c33d42e9df6cbd00467209fdc146ce0bd67395f2b3f0b7d3`.
The intermediate `b4350d99` run failed only because the first committed gzip
transport had a CRC mismatch; all 2443 pre-existing selected tests passed. The
replacement XZ fixture at `4aba3b42` replays unchanged and passed canonical
strategic parity with 2445 selected tests green.

For blind-start replay, permanent creation order and offline replay restoration
are now exact. `G.playing_cards` remains permanent-deck truth; live IDs restore
canonical card-object identity without exposing future physical draw order.
A complete structurally untouched base deck remains eligible for exact
original-suit/hand-sort mechanics even when those authoritative IDs are present.
Stable keyed-RNG and active-Tag checkpoint capture, parameterless
`SELECT_BLIND` evidence mapping, public/private comparison, canonical
`select_blind_exact` replay, and opt-in append-only production capture are green
at `2ac3ddd4`. Capture is observational only and remains outside the public
run-experience log. The canonical toggle/start/restart path forwards the opt-in
directory at `833b2efe`, including launches routed through
`BalatroAgentToggle.bat --attempt N`.

The first opt-in live attempt,
`balatro-20260909T023742Z-2133a13e-attempt-001`, reached the recorder for every
`SELECT_BLIND` action but wrote no sidecar. Its diagnostic stream classified the
exact defect: process-memory `live_id` values arrive as integral Lua numbers,
the permanent-deck translator normalized them to Python integers, but the shared
hand/deck translator retained floats. The strict replay boundary correctly
rejected the type-mismatched IDs rather than weakening identity checks. The
shared translator now normalizes authoritative `live_id` values while preserving
the older opaque `id` compatibility field used by tactical fixtures. CI is green
at `cedd0f11`. The failed capture did not serialize its private RNG checkpoints,
so the public run and diagnostics cannot be converted into a real replay fixture;
one replacement live transition was required and is recorded below.

The first complete private sidecar,
`balatro-20260909T030757Z-a8d1a02d-attempt-001.blind-start-parity.jsonl`,
captured one coherent first Small-Blind transition with zero active Tags. Its
private post-action RNG matched exactly. Public comparison differed only in
`blind.requirement` / `blind_score`: the live pre-selection observer published
the inactive `G.GAME.blind.chips == 0`, while vanilla's visible blind-select UI
computes 300 from `round_resets.blind_ante`, the Small-Blind multiplier, and
ante scaling. Pinned vanilla source confirms that ownership boundary. The live
observer now installs only exact Red/White pending Small/Big requirements from
`blind_ante`; Bosses, other stakes/decks, missing authority, and unowned endless
Antes are not synthesized by this owner and remain behind their existing
capability gates. CI is green at `9d45292f`. Because that recorded pre-action
snapshot is immutable, it was not rewritten into a pass; the post-repair
replacement below is the authoritative passing fixture.

The post-repair attempt,
`balatro-20260909T090428Z-a5968591-attempt-001`, supplies the first passing real
ordinary Small-Blind start fixture. The repository preserves the original
public observation/decision/action-result rows (sequences 2, 4, and 5) and the
complete private sidecar row unchanged in XZ transport. Decompressed SHA-256
guards are respectively
`1c3823b66bbbc3559332f8f38369507483edec8d49c00007929064c307ad7d64`
and
`f353095e5cd93caee6a82e3ea85b848e7a5f7a14df95fe49d9ea8f21cb81feb5`.
The parameterless `SELECT_BLIND` transition replays through canonical
`select_blind_exact` with the 300-chip requirement, zero active Tags, exact
public before/action/after parity, and exact private post-action RNG parity.
CI is green at `74a5acfa` with 2473 selected tests passing.

The same attempt's unchanged public rows 11–13 preserve its first successful
ordinary `END_ROUND` boundary. Pinned vanilla inspection exposed four exact
gaps in the canonical path: the displayed skip Tag leaked into active-blind
callbacks after selection; missing Red/White reward/cleared-requirement facts
were translated as zero; the cash-out owner omitted `cashout{ante}` deck
shuffle; and shop entry did not reset score, hands, discards, or the blind
shell. These are repaired at `6e7c59c4`. The unchanged boundary now rebuilds
from the complete live-ID deck plus the already-preserved post-start RNG
checkpoint and matches the full canonical public shop signature. No additional
private capture was required. Its decompressed public-boundary SHA-256 is
`f77b50b0152d4f9a3a6fbb0969e3cf4e4e8d199c90ff1a260f1bf1e0cd7095e8`.
CI is green at `c304f8d4` with 2476 selected tests passing.

The blind-skip seam is green at `3236a67b`. Its first deterministic replay
exposed a canonical mechanics defect: `skip_blind_exact` advanced the public
`Blind` object to Big but retained the skipped Small Blind's `blind_score`.
The canonical owner now advances both representations to the exact Big target.
GitHub Actions run `34362156416`, job `102501607817`, passed with **2486 passed,
1595 deselected**. The already-recorded public Economy-Tag skip in
`balatro-20260909T030757Z-a8d1a02d-attempt-001` predates this private recorder;
it cannot supply retained progression or skip-count authority and must not be
upgraded into a fixture by inference.

The first post-seam live batch,
`balatro-20260909T142647Z-ff774350`, executed supported Small/Economy skips in
attempt 001 at public sequence 152 and attempt 003 at sequence 140, but emitted
no private sidecar. The public boundaries classified the defect without needing
private diagnostics: the action result advanced to Big while money remained
25/18, then the next observation exposed the completed Economy payout at 50/36.
The canonical injected dispatcher had treated the next Blind identity as a
settled skip even while the immediate Tag event was still pending. It now waits
for the exact Economy result `money + min(40, max(0, money))`; other supported
dispatcher paths are unchanged. CI is green at `0966658f` with **2486 passed,
1596 deselected**. The failed batch has no private authority and is evidence for
the timing repair, not a promotable parity fixture.

The post-settlement batch,
`balatro-20260909T150330Z-186b22a6`, supplies the first complete real supported
Small-Blind/Economy-Tag skip fixture in attempt 005. The unchanged public rows
243–245 and unchanged private sidecar row are preserved in XZ transport. Their
decompressed SHA-256 guards are respectively
`20898032d15279b00397eef9bbc530989931fd0a90df2fdc998e4d98d336cf29`
and
`e79c97beb6634d5c230ca02a49e62085bac0486c2be46988af6ecbd5bc465d2c`.
The live boundary settles the complete exact transition: money 36 -> 72,
Small `Select` -> `Skipped`, Big `Upcoming` -> `Select`, `blind_on_deck`
Small -> Big, skips 0 -> 1, no active Tags, and the visible Tag
`tag_economy` -> `tag_juggle`. The original sidecar verdict remains immutable
and records one `public.after` mismatch. Exact replay localized that mismatch
to translation rather than skip mechanics: while selecting Big, the live
observer's inactive round shell still reported `round.chips == 0` even though
the visible pending `Blind.requirement` was 7500. `BalatroStateTranslator` now
publishes that already-observed requirement as `blind_score` during
`BLIND_SELECT`; it does not synthesize unsupported requirements. The unchanged
fixture now passes canonical public and private replay at `9c0d5c68`. GitHub
Actions run `34375666032`, job `102547699010`, passed with **2488 passed, 1596
deselected**.

The canonical public Buffoon evidence seam is green at `9daea5a4`. It adds no
pack mechanics or policy layer: final Buffoon selections and skips are extracted
from durable live rows into the frozen R3 action vocabulary, while headless
evidence wrappers call `choose_pack_option_exact` / `skip_pack_exact` directly.
GitHub Actions run `34377040125`, job `102552347902`, passed with **2495 passed,
1596 deselected**. The existing live batch `balatro-20260909T150330Z-186b22a6`
contains multiple genuine Buffoon selections, but its public log intentionally
does not contain the ordered visible choice roster, remaining-pick count, or
`PACK_INTERRUPT` return origin. Those rows are evidence that the production
path executes, not sufficient authority for headless replay.

The exact private Buffoon capture/replay seam is green at `ccb1cc88`. It records
only the missing pre-action authority, verifies the planned visible target by
area index, label, center, and live ID, and compares the normal public post-state
after canonical `CHOOSE_PACK_OPTION` or `SKIP_PACK` replay. Final admitted pack
choice/skip consumes no RNG, so no RNG state is captured. GitHub Actions run
`34378808960`, job `102558247537`, passed with **2507 passed, 1596 deselected**.
The first natural capture `balatro-20260909T190805Z-9926231c-attempt-001`
originally reported `public.after`. The mismatch was solely the missing
re-admission of unchosen Droll Joker to the observed common generation pool;
the selected Shoot the Moon correctly remained suppressed after ownership.
The canonical R3 pack owner was repaired at `6f0a57ce`, the exact two-choice
regression corrected at `19c3af33`, and GitHub Actions run `34394979554`, job
`102612318553`, passed with **2510 passed, 1596 deselected**. Buffoon pack parity
is complete for the required representative R5 gate.

The held-Planet public evidence seam is green at `17be3ae6`. It adds no new
mechanics or action authority: durable live rows map to the existing
`USE_CONSUMABLE` contract, and the simulator wrapper calls `use_planet_exact`
directly. GitHub Actions run `34396027499`, job `102615838664`, passed with
**2520 passed, 1596 deselected**. The public snapshot already carries the held
Planet, hand levels, `last_tarot_planet`, and Constellation state. The remaining
private replay authority is exactly Balatro's per-center
`G.GAME.consumeable_usage` counts plus `G.GAME.consumeable_usage_total`; these
are not policy observations and must stay in the opt-in sidecar.

The exact private held-Planet capture/replay seam is green at `452222e7`. It
captures stable complete SHOP public state together with per-center usage
count/set/order records and all five aggregate counters, restores
`consumable_usage_observed=True`, and replays through the canonical
`use_planet_exact` owner. Vanilla's exact pre-first-use state leaves both usage
tables nil; the capture normalizes only that paired-nil state to the five zero
counters that `set_consumeable_usage` creates before its first increment.
Partial, malformed, unknown, inconsistent, drifting, non-SHOP, targeted,
Tarot, and Spectral cases fail closed. The recorder is opt-in through
`--held-planet-parity-directory` and does not change normal decisions. GitHub
Actions run `34398260070`, job `102623415051`, passed with **2541 passed, 1596
deselected**.

The first natural held-Planet attempt on runner revision `39c69f82` bought
Uranus in SHOP, deliberately retained it through `END_SHOP`, selected the next
blind, and ended immediately after the transition into `SELECTING_HAND`. This
does **not** establish a D7 refusal or a general consumable-hoarding defect: the
canonical runtime evaluates held consumables before ordinary hand play, while
Planet timing intentionally waits for `SELECTING_HAND` so it can use the dealt
hand and blind pace. Hermit, Temperance, and Wheel are the only validated
no-hand-target SHOP-use families, under their existing mechanical conditions.
The attempt ended one decision before D7 could emit `USE_CONSUMABLE`, so no
sidecar was expected from that file.

That attempt did expose that the private capture/replay seam itself admitted
only SHOP checkpoints. Exact Planet use and capture were extended fail-closed
to stable `SELECTING_HAND` checkpoints at `f5a9230a` and `6adab3f`; focused
natural in-round coverage landed at `40daa507` and the canonical normalized
Planet hand-key assertion at `b2c3750a`. GitHub Actions run `34413383953`, job
`102672681684`, passed with **2546 passed, 1596 deselected**. No production
consumable timing or shop acquisition policy changed. A natural sidecar on the
current HEAD is still required to close held-Planet parity.

The audited Joker-sale public evidence seam is green at `5a27e22b`. The first
CI attempt correctly rejected a mislabeled unsupported-Juggler regression; the
fixture identity was corrected without changing production behavior. GitHub
Actions run `34421799213`, job `102698626846`, passed with **2557 passed, 1596
deselected**. Every available historical live `SELL_JOKER` decision and
action-result row predates this repair and omits the owned `joker_index`. The
sold Joker is visible only by comparing post-state, which R5 must not use to
infer the planned action target. No historical sale row is therefore promotable
unchanged. A natural current-HEAD sale fixture remains required, but its live
request is deferred while independent R5 work continues.

The representative Boss-start code seam is green at `e185397a`. Pinned vanilla
shows that the public Boss pane reads
`round_resets.blind_choices.Boss`, indexes the matching `G.P_BLINDS` center,
and displays `get_blind_amount(blind_ante) * center.mult` together with that
center's reward. The process-memory observer previously published only
`type=BOSS` with null identity and a zero target before selection, so the
existing exact blind-start checkpoint could not restore any Boss even though
R2 already owns every Boss start route. The canonical observer now publishes
exact pending center key, name, requirement, and reward for Red/White and
leaves missing or inconsistent choice/center state incomplete. The existing
checkpoint then replays the smallest start-inert representative, The Tooth,
through `select_blind_exact` without a new action or replay schema. GitHub
Actions run `34423267134`, job `102703054698`, passed with **2560 passed, 1596
deselected**.

All available historical Boss starts predate this observer repair: their
pre-action public rows contain null Boss identity/zero requirement and they do
not carry the private keyed-RNG checkpoint needed to verify the start shuffle
and deal. They remain diagnostic evidence only and cannot be normalized into a
passing fixture. A natural current-HEAD Boss-start fixture remains required but
is deferred while independent R5 work continues.

The RNG/shuffle/draw coverage audit localized one missing private fact in the
otherwise-green real Small-Blind start replay. The fixture already compares the
public dealt hand and exact post-action keyed RNG, but its sidecar did not retain
the remaining physical `G.deck.cards` order, so it could not prove the next
draw sequence. The existing blind-start checkpoint now captures that order only
as private permanent-card live IDs, verifies the complete pre-start composition,
and compares the exact headless post-deal draw pile. Sparse, duplicate,
non-integral, unreadable, or composition-drifting IDs fail closed; public
evidence remains unchanged and cannot see the order. Older sidecars remain
readable with the field absent but do not satisfy this stronger gate. GitHub
Actions run `34424062376`, job `102705412026`, passed with **2570 passed, 1596
deselected**. A natural current-HEAD blind-start sidecar with the new private
field remains required and is deferred while independent R5 work continues.

The owned-deck composition gate is now green from the existing real Small-Blind
fixture. The live-before state contains exactly 52 permanent playing cards with
52 unique authoritative integral live IDs and exactly one copy of every Red Deck
base rank/suit identity. This validates the permanent `G.playing_cards`-derived
composition without promoting physical `G.deck.cards` order into public truth.
No supported frozen action currently performs a deterministic playing-card
acquisition or conversion end to end: `BUY_CARD` is unavailable, Tarot/Spectral
conversion is outside the admitted Planet-only `USE_CONSUMABLE` slice, and R4
Play still fails closed before unsupported destruction callbacks. The existing
canonical destruction helper therefore remains future exact-expansion material;
no synthetic mutation action or inference from post-state was added.
GitHub Actions run `34458486597`, job `102810415392`, passed with **2571 passed,
1596 deselected**.

## Completed priority parity gates

- ordinary shop paid reroll;
- representative ordinary Joker purchase;
- representative supported Voucher redemption;
- ordinary Small-Blind start and clear/cash-out;
- supported Small-Blind/Economy-Tag skip flow;
- representative Buffoon pack choice;
- audited natural Joker sale;
- owned-deck composition.

## Remaining priority parity fixtures

- held Planet use — recorder/replay code is green, but the natural live fixture
  is temporarily deferred at the user's request and remains incomplete;
- representative Bosses — pending public identity and exact Tooth-start replay
  are green; a natural current-HEAD private fixture is deferred because every
  historical Boss start predates the identity repair and lacks its RNG
  checkpoint;
- RNG/shuffle/draw — exact private post-deal order capture/comparison is green;
  a natural current-HEAD sidecar is deferred because historical sidecars lack
  this private field;
- economy transitions;
- tactical PLAY_CARDS/DISCARD_CARDS decisions and resulting state.

R5 compares canonical state/action/transition evidence, not screenshots or ad-hoc prose logs. Simulator-private physical draw order and RNG state remain private unless a fixture explicitly compares deterministic replay authority at the private simulator boundary; they are never leaked into policy-visible evidence.

## Exact next task

### Economy transition checkpoint: live interest-cap authority

The first economy transition slice is complete at `d3e053de`. The canonical
live observer now publishes exact nonnegative `G.GAME.interest_cap` authority,
and `BalatroStateTranslator` preserves it fail-closed. R5 Voucher evidence now
asserts the exact Seed Money ordering of money debit (`25 -> 15`) and interest
cap mutation (`25 -> 50`), while missing or malformed live authority remains
unobserved rather than inferred. The affected local suites pass at **39
passed**. GitHub Actions run `34464065200`, job `102828384415`, passed for the
published commit; the unauthenticated public API exposed job success but
returned **403** for raw logs, so the CI pytest passed/deselected summary could
not be independently read and is not claimed here. The next economy task must
start by re-fetching this branch and roadmap, then continue only with the next
uncovered supported economy transition.

### Economy transition checkpoint: discount Voucher evidence

The next deterministic economy slice is green in the working tree. R5 public
Voucher evidence now covers the canonical `Clearance Sale` transition and its
`Liquidation` upgrade through the shared `ShopTransitionEngine`: each purchase
debits exactly `$25 -> $15`, while observed shop discount changes `0 -> 25`
and `25 -> 50`, with the exact ordered Voucher ownership in each after-state.
The focused R5 Voucher plus affected R2 owner suites pass at **22 passed**;
the earlier affected economy checkpoint remains **27 passed**. This adds no
live authority and does not promote the missing natural Seed Money/Money Tree
fixture; that fixture remains deferred until a real `BUY_VOUCHER` boundary is
captured. The next economy task must continue from the remaining uncovered
supported mutation after re-fetching this branch. Reroll-cost authority remains
private to the simulator transition and is intentionally not leaked into the
public evidence signature.

### Deterministic R5 edition-rate Voucher evidence checkpoint

The next uncovered public economy mutation is now covered in the R5 Voucher
parity boundary: `Hone` changes the observed Joker edition-generation rate
from `1.0 -> 2.0`, and its ordered `Glow Up` upgrade changes it from
`2.0 -> 4.0`, with the exact `$25 -> $15` purchase debit and Voucher ownership
order preserved. The canonical transition owner was unchanged. Focused R2
owner plus R5 parity validation passes at **29 passed, 0 failed, 0 skipped**.
This is deterministic repository evidence only; no natural live fixture is
promoted by this checkpoint.

### Deterministic R5 reroll-cost Voucher evidence checkpoint

The next uncovered public economy mutation is now covered in the R5 Voucher
parity boundary: `Reroll Glut` preserves the exact `$25 -> $15` purchase debit
and ordered `Reroll Surplus -> Reroll Glut` ownership after the upgrade
purchase. The canonical reroll-cost transition owner was unchanged; its
persistent/current reroll-cost mutation remains simulator-private and is
covered by the existing R2 owner suite rather than being leaked into public
evidence. Focused R5 Voucher parity validation passes at **16 passed, 0
failed, 0 skipped**. This is deterministic repository evidence only; no
natural live fixture is promoted by this checkpoint.

### Deterministic R5 main-shop-size Voucher evidence checkpoint

The next uncovered supported economy mutation is now covered in the R5 Voucher
parity boundary: `Overstock` and its ordered `Overstock Plus` upgrade preserve
the exact `$25 -> $15` purchase debit and Voucher ownership order. The canonical
shop-size redemption owner in
`games/balatro/env/shop_size_voucher_redemption.py` is unchanged; its private
main-shop replenishment remains separate from public parity evidence. Focused R5
Voucher parity validation passes at **18 passed, 0 failed, 0 skipped**. This is
synthetic deterministic repository evidence only and does not promote a live
fixture. The next uncovered supported deterministic economy transition is the
Hieroglyph/Petroglyph ante-and-round-allowance pair; the natural Money Tree,
held-Planet, Joker-sale, Boss, and strengthened blind-start fixtures remain
live-only or deferred.

### Independent R5 tactical evidence checkpoint

The durable live-log tactical adapter now has deterministic R5 coverage for
both frozen tactical action families: `PLAY_CARDS` and `DISCARD_CARDS`. The new
discard regression converts an unchanged successful observation/decision/action
result boundary through `successful_tactical_evidence_from_run_rows` and
compares it through the shared public trajectory comparator. The focused
tactical suite passes at **5 passed**. This does not change canonical tactical
ownership or promote a live fixture; the active roadmap task remains economy
transitions.

### Live supervisor crash repair checkpoint

The interrupted Money Tree batch exposed a production-only replan crash after
loss: `BuildAwareShopArbiter._best_visible_bond_pair()` called `_economics()` on
`PlaybookJokerAcquisitionPolicy`, whose wrapper lacked that canonical contract.
The playbook wrapper now delegates `_economics()` through the existing
`JokerAcquisitionPolicy` with the same Red/White D2 thresholds. The focused
playbook policy suite passes at **8 passed** and the adjacent shop-arbiter and
strategy-authority suites pass at **27 passed**. This repair changes no R5
phase gate and does not start R6; it makes future bounded live attempts safe to
continue after a loss.

### Deterministic R5 gate checkpoint

The current clean branch passes the GitHub Actions-equivalent deterministic
Balatro selector at **2591 passed, 0 failed, 0 skipped, 1596 deselected**.
A fresh current-HEAD verification completed in **115.00s** with the same green
result. The live Win32 read boundary now has a bounded fail-closed guard in
[games/balatro/live/runtime/process_memory.py](games/balatro/live/runtime/process_memory.py)
for the exact synchronous `ReadProcessMemory` risk pattern observed after
`END_ROUND -> SHOP`; the observer remains under R5 gate until the live fixture is
captured successfully. R6 and every later phase remain hard-blocked until the R5
natural-fixture exit gates and all R5 exit criteria are complete; this green
deterministic gate does not authorize a phase transition.

### Bounded process-memory result transport repair

The bounded Win32 read guard now retrieves a completed worker result with a
bounded `Queue.get()` instead of the racy `multiprocessing.Queue.empty()` check.
This preserves the fail-closed timeout behavior while preventing a successful
fast native read from being misclassified as missing output. The focused guard
suite passes at **2 passed**; the affected R5/economy/live selector passes at
**31 passed, 0 failed, 0 skipped, 4158 deselected**. The Balatro process is
currently present and responsive, but no current-HEAD natural Money Tree
purchase boundary has been captured or promoted. The next active R5 task remains
that live fixture; no synthetic or incomplete batch output is promoted.

### Deterministic Money Tree evidence checkpoint

R5 public Voucher evidence now covers the dependent `Money Tree` upgrade using
the existing canonical interest-cap owner: money debits exactly `$25 -> $15`,
interest cap changes `50 -> 100`, and ordered ownership changes from
`[v_seed_money]` to `[v_seed_money, v_money_tree]`. The focused Voucher suite
passes at **13 passed**. This is synthetic deterministic evidence only; the
natural live Money Tree fixture remains deferred and is not marked complete.

### Deterministic R5 Hieroglyph/Petroglyph evidence checkpoint

The next uncovered supported economy transition is now covered in the R5
Voucher parity boundary: `Hieroglyph` preserves the exact `$25 -> $15`
purchase debit, ordered ownership, Ante `2 -> 1`, next-round hands `4 -> 3`,
and current hands `4 -> 3`; its dependent `Petroglyph` purchase preserves the
same debit, ordered `[v_hieroglyph, v_petroglyph]` ownership, Ante `1 -> 0`,
next-round discards `4 -> 3`, and current discards `4 -> 3`. The canonical
owner in `games/balatro/env/ante_voucher_redemption.py` is unchanged; the
existing private `blind_ante` mutation and R2 fail-closed legality coverage
remain authoritative. Focused R5 Voucher parity plus both affected R2 owner
suites pass at **35 passed, 0 failed, 0 skipped**. This is synthetic
deterministic public evidence only and does not promote a natural live fixture.

### Natural Seed Money fixture checkpoint

The current-HEAD live fixture
`balatro-r5-current-head-seed-money.buy-seed-money.jsonl` is now promoted and
replays through the canonical owner. It proves a real successful `BUY_VOUCHER`
for Seed Money with money `27 -> 17`, observed interest cap `25 -> 50`, and
ordered public ownership `[] -> [v_seed_money]`. Replay initially exposed two
canonical owner defects: live Voucher metadata dropped `area_index`, and exact
interest-cap redemption left the dependent `v_money_tree` generation-pool
eligibility stale. Both are repaired with focused coverage. The real fixture
suite plus affected R2/R5 tests pass at **25 passed**. This completes the
natural Seed Money fixture only; Money Tree still needs a current-HEAD natural
fixture, and the remaining held-Planet, Boss, and strengthened blind-start
natural gates remain deferred. The later natural Joker-sale checkpoint is now
complete. R6 remains hard-blocked.

### Natural face-up deal and representative Boss-start checkpoint

User-run session `balatro-20260911T180643Z-11e1fb92` completed all five
bounded production attempts and produced eleven complete blind-start sidecars.
No attempt purchased `v_money_tree`, so the natural Money Tree gate remains
open. The repaired live observer exposed one canonical simulator defect across
the otherwise-supported starts: ordinary deck-to-hand movement left simulator
cards face down while live Balatro reported exact front-facing hand cards.
The shared round-start and one-card draw owner now mirrors vanilla
`CardArea:emplace`: every ordinary draw is authoritatively face up before the
existing House, Mark, Wheel, or Fish owner applies any supported exception.

The unchanged attempt-1 Small-Blind and `The Hook` sidecars now replay with
zero public, keyed-RNG, or 44-card private draw-order differences. Both exact
public triplets and private sidecars are promoted with decompressed SHA-256
guards. The strengthened Small-Blind fixture is refreshed to the current
facing-aware observer evidence; the older pre-facing fixture remains a
fail-closed regression and is not treated as authoritative for facing. Focused
owner, Boss, parity, and fixture validation passed at **77 passed**. Repair and
fixture commit `deb34992451a8b67851b1929e0e8b5242c1c2d31` passed GitHub
Actions run `34634258937`, job `103378212096`; the actual job log reports
**2624 passed, 1602 deselected in 121.41s**.

### Natural Money Tree follow-up batch

User-run session `balatro-20260911T184407Z-f8230dbb` completed all five
bounded production attempts, stopped normally at the attempt limit, and lost
at Antes 7, 5, 4, 5, and 2 after 155, 126, 72, 106, and 49 actions. Every
recorded action succeeded and the session produced no diagnostic failure
artifact. Attempt 1 naturally bought Seed Money, reached Ante 7 with its
dependency active, and subsequently bought Crystal Ball, Paint Brush, Reroll
Surplus, and Overstock; Money Tree was never offered or purchased. The other
attempts also produced no `v_money_tree` offer or purchase. No fixture is
promoted from this batch, and the exact next task remains another bounded
natural Money Tree capture.

User-run follow-up session `balatro-20260912T012234Z-9a3938ad` also completed
all five bounded attempts, stopped normally at the attempt limit, and lost at
Antes 2, 5, 7, 4, and 5 after 39, 93, 185, 109, and 102 actions. All 528
recorded actions succeeded and no diagnostic failure artifact was produced.
The Ante-7 attempt bought seven vouchers, but no attempt was offered or
purchased Seed Money, and none was offered or purchased Money Tree. No fixture
is promoted; the exact next task remains another bounded natural Money Tree
capture.

### Current R5 status

- Deterministic R5 selector: **2624 passed, 0 failed, 0 skipped, 1602 deselected** in the actual GitHub Actions job log for `deb34992451a8b67851b1929e0e8b5242c1c2d31` (run `34634258937`, job `103378212096`).
- Natural Seed Money fixture: **complete** at current HEAD.
- Natural Money Tree fixture: **ON HOLD BY USER DIRECTION**; it remains required and synthetic replay is not a substitute.
- Natural audited Joker sale: **complete** from the current-HEAD Jolly Joker fixture.
- Natural held Planet fixture: **complete** from the current-HEAD Uranus fixture.
- Strengthened blind-start fixture: **complete** with current-observer facing authority and exact private post-deal draw order.
- Representative natural Boss-start fixture: **complete** from the current-observer `The Hook` fixture, with exact public, keyed-RNG, and private draw-order replay.
- Live supervisor reliability: **bounded read guard repaired; natural fixture capture is on hold**. The guard fails closed when a native read exceeds its timeout, and the successful result path is deterministic-tested. Do not treat the guard repair as a completed natural Money Tree fixture.
- The earlier failing run `34501743361` is superseded by the successful current-HEAD run `34556158163`; its actual log is available and supplies the count above.
- R6: **UNBLOCKED BY EXPLICIT USER DIRECTION** with the missing natural Money Tree fixture retained as an R5 exception; later phases remain blocked on their own roadmap gates.

### Next actions

1. Begin B0 with the random legal strategic baseline on the versioned observation/action interface.
2. Keep the natural Money Tree capture on hold until the user explicitly resumes it.
3. Keep unsupported Boss skips/rerolls, pack/pre-blind/Verdant sales, shop buy-and-use, Tarot/Spectral mechanics, booster Planet choices, policy tuning, and playing-card purchases fail-closed. `BUY_CARD` and `REROLL_BOSS` remain unavailable.

## R5 exit criteria

- one canonical comparator/evidence path per public transition family, reusing frozen production/R3 action identifiers;
- representative tactical Play/Discard parity passes on captured live evidence;
- representative strategic fixtures above pass on captured live evidence;
- mismatch output identifies the first differing state/action/transition field rather than only returning false;
- no hidden-information leakage into policy evidence;
- deterministic replay/private authority remains separate from public parity signatures;
- parity failures route back to the first wrong canonical owner rather than being normalized away.

---

# R6 — environment performance gate — COMPLETE / GREEN

Representative semantics and parity are green for the promoted surface; the
natural Money Tree exception is retained explicitly above. Measure in this
order:

- headless steps/sec — **COMPLETE / GREEN**;
- complete Red/White runs/minute — **COMPLETE / GREEN**;
- parallel scaling — **COMPLETE / GREEN**;
- tactical-bridge cost — **COMPLETE / GREEN**;
- serialization/restore overhead — **COMPLETE / GREEN**;
- deterministic replay overhead — **COMPLETE / GREEN**.

Do not trade exactness for throughput before this phase.

## R6 completion condition

All six ordered performance measurements are green and recorded below. R6 is
closed. Its host-local measurements remain reference evidence rather than CI
speed thresholds.

### Headless steps/second baseline checkpoint

Commit `9e07eaaef2e427b1b41c9b00ef71d7cea64401ac` adds the canonical fixed
`red-white-pristine-small-blind-start-v1` workload and the
`balatro-r6-headless-throughput-v1` machine-readable report. Each measured step
executes the real pristine Red Deck / White Stake Small-Blind start transition,
including state copy, keyed-RNG shuffle, lifecycle transition, deal, and facing.
The deterministic regression suite pins the workload, warmup and measurement
counts, immutable input template, report calculation, CLI JSON, and fail-closed
invalid-clock/count behavior with an injected clock.

The host-local reference invocation used 100 warmup steps and 1,000 measured
steps. It measured 3.2191163999959826 seconds and 310.64425008093775 steps/second.
This is a reproducible reference measurement, not a portable CI threshold.
Commit `9129e3099d66c2a18587457a09a2465fcc6ca909` adds the R6 tests to the
deterministic CI selector. GitHub Actions run `34667163208`, job
`103481298812`, passed with **2631 passed, 1602 deselected in 115.59s** in the
actual job log. The first R6 gate is therefore complete; the exact next task is
the complete Red/White runs/minute baseline recorded below.

### Complete Red/White runs/minute baseline checkpoint

Commit `1cbf04fecac622bc3eeeedda5bbb257c202af26f` adds the fixed
`red-white-first-small-blind-single-card-loss-v1` workload and the
`balatro-r6-complete-runs-throughput-v1` machine-readable report. The repository
does not yet contain a concrete `HeadlessBackend`, so this workload does not
promote a test fake. It composes the canonical first-Small-Blind start owner with
four canonical single-card Play transitions and independently validates the
authoritative Red Deck / White Stake terminal loss: Ante 1, round 1, zero hands
remaining, and score 56 below the 300-chip requirement. It is a complete losing
episode throughput baseline, not an Ante-8 competence claim.

The host-local reference invocation used 100 warmup runs and 1,000 measured
runs. All 1,000 measured episodes completed in 8.109855300048366 seconds, or
7398.405739698237 runs/minute. This is a reproducible reference measurement,
not a portable CI threshold. GitHub Actions run `34667640114`, job
`103482704764`, passed with **2640 passed, 1602 deselected in 61.54s** in the
actual job log. The second R6 gate is therefore complete; the exact next task is
the parallel-scaling baseline recorded below.

### Parallel-scaling baseline checkpoint

Commit `06462a44a34916760a30c6c212f3d696f75e6abb` adds the
`balatro-r6-parallel-scaling-v1` strong-scaling report over the same fixed exact
terminal episode. Every configuration uses independent process-owned workers,
per-worker warmup before timing, an exact balanced partition of the same 1,000
measured runs, and per-batch completion validation. Executor startup and warmup
are excluded from elapsed measurement; no wall-clock threshold is enforced.

The host-local reference used worker counts 1, 2, and 4, ten warmup runs per
worker, and 1,000 measured runs per configuration. One worker completed in
7.683218700112775 seconds at 7809.22714058879 runs/minute. Two workers completed
in 3.8296489000786096 seconds at 15667.232575489728 runs/minute, 2.0062462383836452x
scaling and 1.0031231191918226 efficiency. Four workers completed in
1.9301252999575809 seconds at 31086.06472404597 runs/minute, 3.980683896678434x
scaling and 0.9951709741696085 efficiency. These are host-local reference
measurements, not portable thresholds. GitHub Actions run `34668058861`, job
`103483936025`, passed with **2649 passed, 1602 deselected in 119.36s** in the
actual job log. The third R6 gate is complete; the exact next task is the
tactical-bridge cost baseline recorded below.

### Tactical-bridge cost baseline checkpoint

Commit `a10be92db4e785538a10571b9a6707d4a312d3ae` adds the fixed
`red-white-first-small-blind-first-card-play-v1` comparison and the
`balatro-r6-tactical-bridge-cost-v1` machine-readable report. Both paths reuse
the same immutable dealt Red/White input. The direct side invokes the canonical
Play transition; the bridged side invokes the existing production-shaped
`decide(state)` tactical seam, including its policy-safe observation copy and
visible-card mapping, then reaches the same canonical Play owner. The benchmark
validates equivalent public state and RNG after both paths.

The host-local reference used 100 warmup steps and 1,000 measured steps per
path. Direct execution took 1.2041587999556214 seconds at 830.4552522780671
steps/second. Bridged execution took 1.2092440000269562 seconds at
826.9629619644243 steps/second. Measured bridge overhead was
0.000005085200071334839 seconds/step, or 0.004223031108124831 relative to direct
elapsed time. These are host-local reference measurements, not portable
thresholds. GitHub Actions run `34668446805`, job `103485044083`, passed with
**2654 passed, 1602 deselected in 108.44s** in the actual job log. The fourth R6
gate is complete; the serialization/restore overhead checkpoint is recorded below.

### Serialization/restore overhead checkpoint

Commit `69ec3a2bbf266e7451d91ab297f1e9b9ac9d2d4c` adds the versioned
`balatro-headless-run-state-v1` canonical round trip at `HeadlessRunState` and
the `balatro-r6-serialization-cost-v1` machine-readable benchmark. The format is
JSON-compatible data rather than pickle or `deepcopy`. It preserves shared
playing-card identity across the public state, simulator-private zones, and
retained creation order; it also preserves keyed RNG and retained blind
progression. Exact continuation after restore is regression-tested. Malformed
snapshots and currently unsupported object inventories such as Jokers and pack
choices fail closed.

The host-local reference used a post-first-card-Play state, 100 warmup round
trips, and 1,000 measured operations per path. Its canonical payload is 17,877
bytes. Serialization took 0.3158465001033619 seconds at 3166.0949216557615
states/second; restore took 0.2708902000449598 seconds at 3691.532583437974
states/second. Combined round-trip cost was 0.0005867367001483217 seconds/state,
or 1704.3419982885152 round trips/second. These are host-local reference
measurements, not portable thresholds. GitHub Actions run `34669013814`, job
`103486662682`, passed with **2667 passed, 1602 deselected in 120.29s** in the
actual job log. The fifth R6 gate is complete; the exact next task is the final
deterministic replay-overhead baseline recorded below.

### Deterministic replay-overhead checkpoint

Commit `51b36b64b7609e6b95f58cb04758a12926f3e8c5` adds the fixed
`red-white-first-small-blind-four-play-loss-v1` trajectory and the
`balatro-r6-deterministic-replay-cost-v1` machine-readable report. One reference
capture records the initial dealt boundary and all four post-Play boundaries.
Verified replay then executes the same seeded actions and compares the canonical
versioned state payload at each boundary, covering public state, private zones,
retained order, and keyed RNG. The first mismatch fails closed with its exact
boundary index.

The host-local reference used 100 warmup trajectories and 1,000 measured
four-action trajectories. Baseline execution took 7.1561278000008315 seconds at
139.74037747060413 trajectories/second. Five-boundary verified replay took
9.100346499937586 seconds at 109.88592577292067 replays/second. Verification
overhead was 0.001944218699936755 seconds/trajectory, or
0.2716858550145693 relative to baseline elapsed time. These are host-local
reference measurements, not portable thresholds. GitHub Actions run
`34669417940`, job `103487802351`, passed with **2673 passed, 1602 deselected in
119.47s** in the actual job log. All ordered R6 gates are complete and green.

# Active next phase

## O — observation/action encoding — COMPLETE / GREEN

### Exact next task

O is closed. Begin B0 with the random legal strategic baseline. It must consume
the versioned observation/action interface and canonical backend legality, use
explicit reproducible sampling authority, and never synthesize a rescue action
for an empty mask. Do not begin the deterministic symbolic/headless baseline
until the random baseline is green and recorded.

- versioned public observation schema — **COMPLETE / GREEN**;
- versioned action schema/mask — **COMPLETE / GREEN**;
- no hidden-information leakage;
- illegal action probability exactly zero after masking;
- Bond-derived signals may be observations/features but not hard-coded strategic authority.

### Versioned public observation schema checkpoint

Commit `438ed6c194f786240f82a589b7d23da975217ae5` adds the immutable
`balatro-red-white-public-observation-v1` schema at the canonical environment
frame boundary. It emits one deterministic 2,444-value vector with stable field
names and fixed-capacity visible zones for the promoted Red Deck / White Stake
surface. Permanent deck and discard composition are canonically ordered while
the policy receives only the public remaining-deck count; simulator-private draw
order, RNG/seed state, and live IDs are never inputs. Face-down hand identity is
masked through the existing canonical public-observation owner before encoding,
including rank, suit, modifiers, history, and permanent metadata. Joker,
consumable, shop, Voucher, Boss, hand-history, and observed generation-pool
features use pinned catalogues. Unknown catalog entries, malformed authority,
unrepresented Joker state, non-finite values, and zone overflow fail closed
instead of truncating or approximating.

Focused local validation passed **23 tests** across the new schema, environment
frame, face-down-card, and Amber Acorn public-observation suites. A direct smoke
test encoded the canonical exact first-Small-Blind headless state at shape
`(2444,)`. The deterministic workflow selector now explicitly includes
`env_o`. GitHub Actions run `34687591983`, job `103537194284`, passed; the
actual job log reports **2684 passed, 1602 deselected in 120.81s**. The public
observation task is complete and green. The exact next task is the versioned
action schema/mask above.

### Versioned action schema/mask checkpoint

Commit `766c830ce7515b479fea307730bcf76427de14f9` adds the immutable
`balatro-red-white-public-action-v1` schema. Its 27 stable slots are derived in
the frozen training-action contract order and expand only the bounded public
parameters for main-shop inventory, booster inventory, owned Joker sales,
Buffoon choices, and held consumables. Encoding and decoding round-trip through
the existing `EnvAction`; unsupported aliases, extra parameters, out-of-range
slots, and duplicate legal actions fail closed.

The legality mask consumes actions returned by canonical transition owners; it
does not duplicate phase, resource, or mechanics rules. Probability application
sets every illegal slot to exact `0.0`, renormalizes remaining legal mass, and
returns an all-zero terminal mask without inventing a fallback action. Invalid
shape, schema version, non-finite/negative probability, and zero mass over a
nonempty legal set fail closed. Focused local schema, observation, frozen
contract, and canonical shop-legality validation passed **82 tests**. GitHub
Actions run `34687961713`, job `103538171035`, passed; the actual log reports
**2695 passed, 1602 deselected in 119.18s**. O is complete and green.

## B0 — RL baseline infrastructure — IN PROGRESS

### Exact next task

Implement the random legal strategic baseline using the versioned observation
and action schema plus canonical backend legality. Sampling must be reproducible
under an explicit baseline seed, must never sample a masked action, and must
fail closed on an empty nonterminal legal mask. Add focused deterministic tests
before recording the checkpoint.

Before PPO:

1. random legal strategic baseline;
2. deterministic symbolic/headless baseline;
3. fixed seeded evaluation set;
4. unseeded evaluation set;
5. Ante reached / Ante 8 clear / survival/economy diagnostics;
6. promotion and regression thresholds defined before training results are observed.

## PPO — NOT STARTED

Do not begin until R-phase exactness, representative parity, performance, observation/action encoding, and baseline gates are satisfied.

Primary promotion metric remains:

**P(clear Ante 8 | Red Deck, White Stake, normal mode).**

Only after controlled Red/White promotion should higher stakes or additional decks become active development targets.
