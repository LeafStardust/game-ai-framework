# Post-Pon discard sent before layout settled

Review of the unmatched discard from the five-game run found that the recorded
before-input frame still showed the Pon cut-in and extra standing called tiles
beyond the eleven-tile concealed hand. The first eleven visible tiles matched
the reader's shortened hand, so the previous complete-multiset check alone
accepted that transient prefix. The next saved frame shows 1 Man selected,
not discarded. Later, the server observed a different discard. The evidence
supports premature post-call input; it does not establish OS delivery loss.

For ActionChiPengGang layouts, visual verification now examines the next two
standing-tile positions beyond the expected concealed hand. If the ordinary
unchanged-confidence classifier recognizes a full standing tile there, preflight
rejects the animation. Neither expected reader labels nor new relaxed thresholds
are used. The usual full-hand identity, separate stable frames, board freshness
and foreground checks remain. Offline replay rejects the original before-input
frame and accepts the later frame's cleared tail. That later frame's selected
first tile still must independently pass ordinary hand recognition; a clear tail
alone does not authorize a click. Unit tests use existing synthetic/reference
samples rather than publishing another private session snapshot.

The logged stale/incomplete-capture decision failure now receives the same
single fresh-attempt allowance as request expiry in automatic mode. A new
request rereads and revalidates capture; neither incomplete data nor stale
proposals are accepted. A repeated rejection remains bounded. Monitor behavior
and the existing one-time verified mouse retry are unchanged. This improves
transient-failure recovery without claiming every capture rejection is transient.

Validation: 952 passed, one skipped. No game or agent was launched, no native
input was sent, and no existing session recordings were changed. The next
user-started run must verify post-Pon input and any fresh capture retry live.
