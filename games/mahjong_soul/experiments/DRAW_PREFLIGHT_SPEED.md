# Draw preflight work

The October 25 batch repeatedly attempted verification while the draw/replacement slot was not yet visible. Retained frame inspection confirmed the standing hand was present while the expected separated draw slot was still table background.

For calibrated `ActionDealTile` layouts, verify the last slot first. An unfinished draw now exits before sampling the standing hand. Successful checks still read every tile, restore slot order, compare the full hand with the reader and require the existing second independent stable frame. Post-call layouts retain their existing verification order and animation guard.

The ambiguous-tile monochrome fallback now uses the same exact packed absolute-distance implementation as RGB matching, with a per-instance bounded 2048-entry cache. Monochrome values are repeated across three channels, preserving the original mean absolute difference exactly. Thresholds, margins and red-ink criteria are unchanged.

Offline replay of 25 retained local frames (15 rejected, 10 accepted) found zero acceptance, tile-label or returned-sample differences. One local timing pass measured rejected-check medians of 128.95 ms before and 98.09 ms after; accepted-check medians were 55.63 ms before and 71.35 ms after. These small, cache-sensitive measurements were collected while tests were running and are not a live end-to-end latency benchmark. The benefit is a bounded reduction in wasted verification work, not elimination of client animations or a demonstrated one-second live input guarantee.

Validation: the full suite passed 981 tests with one skipped after the implementation; an additional targeted early-exit regression was added and run afterwards. Existing recorded red-five fixtures now resolve samples by coordinates rather than assuming sampling call order. No new session images or private snapshots were published. No game or agent was started.

Next: validate the change during the user-started normal three-game run, then compare live latency and transient missed offers. Further optimization should prioritize capture and button-animation timing while retaining verification guards.
