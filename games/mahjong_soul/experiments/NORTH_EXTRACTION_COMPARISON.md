# North extraction comparison

Native Kita now compares the hand after removing North with the best ordinary discard. It retains North if extraction increases Shanten. For a pair or triplet, equal Shanten must also preserve the best live ukeire. When these checks tie, bank Kita and its replacement draw. These are immediate shape comparisons, not a full expected-score search.

Qualified Kokushi and All Honors targets retain North through the existing Yakuman qualification and feasibility model. Offered wins still precede extraction. Decisions record `north_evaluation` in the journal; terminal output remains recommended actions only.

Auto Kita remains disabled while a North pair/triplet needs evaluation. The native handler can extract it when the comparison permits, one offer at a time. Enabling the client switch after approving one extraction could extract another North and destroy the retained pair, so approval of one Kita is not permission for repeated automatic extractions.

Validation: synthetic North shape and Yakuman cases, equal-Shanten ukeire comparisons, and the full Mahjong suite (980 passed, one skipped). No live agent was started. Next check is the user's normal three-game run.
