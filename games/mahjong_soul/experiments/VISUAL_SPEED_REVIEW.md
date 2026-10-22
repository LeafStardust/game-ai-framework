# Faster visual verification without weaker checks

## Profile and correction

A stable recorded 14-tile pre-input frame from session
`20261022T043546-483121Z`, `frames/0000036.png`, required 5,754 reference
comparisons. A profiler attributed most recognition time to per-channel Python
absolute-difference loops. Its instrumented times are not used as speed claims.

TileVision now pre-packs reviewed RGB samples into independent unsigned 16-bit
integer lanes. A high-bit guard prevents subtraction borrowing between lanes;
per-lane selection computes the same absolute channel difference as the original
scalar formula. Summing the low-byte lanes yields exactly the original mean RGB
distance. No dependency, approximation or new recognition threshold is added.
Reference glyph shapes are also prepared once rather than rebuilt on every
ambiguous sample. A per-instance 2,048-entry LRU stores exact sample-score tuples;
changed pixels get a new calculation. Diagnostics return independent copies.

## Measured scope

[The benchmark](VISUAL_SPEED_BENCHMARK.json) contains seven passes per condition
and the source screenshot hash. Median full hand recognition, including PNG
decode and sampling:

| Condition | Median |
| --- | --- |
| Original scalar distance, no result cache | 208 ms |
| Optimized, cache cleared before each hand | 83 ms |
| Optimized, repeated stable samples | 51 ms |

This single stable hand is about 2.5 times faster cold and 4.1 times faster warm.
It excludes native screenshot capture, PNG encoding, journal writes, mouse input,
client animation and failed preflight retries. It is not an end-to-end click
benchmark and does not promise the same improvement on every hand or machine.

## Preserved behavior and verification

Two actual preflight screenshots, visual stability comparison, full hand/reader
agreement, board token, source freshness and window checks remain. OS mouse press
and release timing is unchanged. Animation and unknown-skin rejection still work.
No live game or agent was started, and no mouse input was sent during development.

Tests prove exact arithmetic on extremes, alternating lanes and seeded random
samples; compare every label's minimum bank distance on reviewed/random samples;
and check unknown rejection, cache bounds and independent diagnostics. Existing
native-input, scoring, route, result-button and assist suites also pass: 883 passed,
one skipped. Tests do not establish live input reliability or strategy strength.

Each action preflight now records `preflight_timing` with elapsed seconds and
success/failure. It measures the complete preflight, including capture and record
work, without adding terminal output. The next user-started AI game can establish
actual decision-to-input improvement and show the remaining animation/IO cost.
The user's unrelated YAKU.md edits are preserved outside this commit.
