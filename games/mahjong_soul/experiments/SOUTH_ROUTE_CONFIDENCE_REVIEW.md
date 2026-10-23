# Reachable attack value and capture timing

Following session `20261023T071725-098919Z`, improve South attack planning
without changing the always-push priority or the ten-slot Yakuman gate.

South projected Han is now weighted by `1 / (1 + 0.25 * route_cost)` when
comparing unfinished routes and candidate discards. Route cost is the existing
route-specific replacement heuristic. This discourages sacrificing useful
winning draws for a distant extra Han. It is not a calibrated win probability
or expected score. Scored Tenpai is exempt; equal-cost high-value targets retain
their advantage. East playbooks do not enable this setting. South versions are
Three-Player v0.3 and Four-Player v0.14.

Tests exercise a reachable three-Han route versus a four-Han route needing four
replacements, the reverse preference when both are equally reachable, and the
scored-Tenpai exemption. This is a bounded heuristic improvement, not evidence
that match win rate has improved. The preceding match alone cannot establish
whether individual losses were policy mistakes or variance.

Visual sampling now sums byte slices rather than individual pixels in Python.
All coordinates, RGB channels, integer rounding, recognition thresholds and
independent frame checks remain identical. An offline comparison on three saved
frames checked every output byte for fourteen samples: median sampling time
21.68 ms before and 6.28 ms after. This is about 3.4 times faster sampling,
roughly 31 ms saved over two full-hand checks; it is not a comparable speedup
of the complete input pipeline. Regression coverage also compares varied crop
sizes against scalar sampling.

Each captured frame now records capture and recording duration separately in
`frame_timing`. This distinguishes screenshot latency from recognition, explicit
waits and disk evidence writes in the next user-started session. Existing
preflight and recommendation-to-submit timing remain. No native press timing,
record-before-input rule, freshness check or confirmation requirement is removed.
The one-second ideal and 1.5-second upper target still require live validation.

No game or agent was started and no native input was sent during development.
