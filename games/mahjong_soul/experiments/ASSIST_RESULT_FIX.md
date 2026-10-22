# Auto Kita and result-control correction

Auto Kita was explicitly disabled in assist preferences. Ordinary three-player
play now requests it ON; four-player play never does. Keep it OFF when a retained
North is needed, when holding a North pair, or while pursuing a qualified Thirteen
Orphans/All Honors plan. Win assistance is reconciled before enabling Kita.
The switch still uses observed-state confirmation, never blind toggle clicks.
Individual North offers retain the existing legal policy and executor.

Result handling had two separate problems: every scan spawned Windows OCR, and
win-detail Confirm plus score-transfer Confirm could have identical round/label/
position keys, suppressing the second screen. Three reviewed templates now cover
win details, score transfer and final match results using both the label and a
separate result heading. Both regions are rechecked before fast-path input.
Unknown layouts retain OCR; verified Continue/Confirm layouts with a recognizable
result heading are cached for subsequent scans within the process. No menus or
new matches are started. Result polls are eligible every 0.2 seconds instead of
0.5, and skip a redundant passive capture immediately before result preflight.

Deduplication now distinguishes result stages. If the same stage remains visible,
allow one retry after at least 1.5 seconds, with a new recognition and stable-frame
check. At most two delivered clicks per round/stage/label/position; an unchanged
animation does not generate unlimited clicks. Input failures still halt.

Tests cover ordinary Auto Kita, North/Yakuman protection, consecutive Confirm
screens, bounded retries and actual screenshot crops recognized without OCR.
The latest saved result images prove the new templates recognize these layouts;
this is not a claim of measured live latency. The first unknown Continue layout
still needs OCR before caching. Live validation requires restarting the agent via
the normal launcher; no live agent was started during this fix.
