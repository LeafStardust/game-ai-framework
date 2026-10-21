# South Attack: adapting the East decision work

## What transfers

The references in [RESEARCH.md](../RESEARCH.md) motivate public-information
planning, separate decision types and full-game evaluation. They do not provide
this agent with trained weights, nor prove that East settings transfer to South.
The actual deployed East upgrade being adapted here is bounded legal-completion
lookahead. Shared exact Yaku/Fu/payment scoring, legal-action validation, native
input checks and journal diagnostics already applied to South before this change.

Three-Player South Attack v0.2 and Four-Player South Attack v0.13 now enable a
separate `attack_completion` objective. East explicitly disables that flag and
keeps its existing settings and direct speed objective. Unpromoted experiments
(call width, always-push East, ready repair/Ron sensitivity) remain unpromoted.

## Attack before speed

Start with South's existing nearest-scoring-distance, 70% improving-copy floor
and maximum-copy-sacrifice shortlist. Keep its original attack-utility baseline.
Only alternatives with the same projected Han, target Yaku and suit qualify.
They cannot increase route cost, lost Dora or pair breakage. Qualified Yakuman
routes bypass this ordinary completion model, retaining the ten-tile and public
feasibility gate. These guards prevent replacing the valuable baseline with a
cheap projected route just because the cheap hand is faster.

For a closed two-Shanten hand without an opponent threat or existing Riichi,
compare baseline plus at most two distinct development alternatives. The shared
model uses at most 2,000 states per candidate and a horizon of at most twelve own
draws, bounded by floor(wall / player_count). Fewer than three remaining own draws
skip the search. Any unavailable shortlisted estimate retains the baseline.

Unlike East's legality-only target, South counts a terminal wait only if exact
Tsumo scoring reaches at least the baseline projected Han (rounded upward).
Known retained red fives are preserved when building hypothetical hands; unknown
future red draws, Riichi, Ura and Ippatsu are not granted. Honor permutations are
not collapsed in this value model because different honors can change Han.
Among qualified options, lower capped completion cost wins; ties retain the
original attack ranking. Detailed logs retain the baseline, evaluated forecasts,
minimum Han and `completion_objective=attack_value_preserving`. Terminal output
remains recommended action only. Native configuration hashes now include these
lookahead source modules.

## What this does not establish

This is bounded, monotonic own-draw planning, not a full expected-points solver.
The threshold is based on projected Han, which can be optimistic. Forecast
continuations may differ from the actual future policy. Future calls, Ron,
Riichi and equal-Shanten repairs are excluded. Hidden hands and wall order are
never used. Three candidate forecasts can add cold-start latency; a recorded
Sanma regression took about 1.77 seconds for the full policy in one local cold
run, not a worst-case guarantee. Freshness and visual guards remain unchanged.

Existing South calls still need a supported valuable Yaku route; East's cheap
opening rules were deliberately not copied. Opponent Riichi still does not
trigger folding. Three-player South keeps North extraction and no Chi. The ten
qualifying Yakuman slots and natural later qualification with enough available
copies/draws are unchanged; Thirteen Orphans still stays Dama.

## Verification and next measurement

Tests exercise actual production routing on a recorded public Sanma request,
a changed selection under a controlled completion estimate, exclusion of cheap
or damaged routes, actual legal-but-low-Han wait rejection, Yakuman bypass,
four-player draw budgeting, unavailable-forecast fallback and East isolation.
These are correctness checks, not win-rate evidence. The older East held-out
outcomes do not establish this South variant's strength. Next evaluate recorded
South decisions and full user-started South AI games with these versions,
including action latency and missed calls. No agent was launched for this work.
