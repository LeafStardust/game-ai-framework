# South losing-game decision review ? October 27, 2026

Reviewed the two losing games from the b090cb6e batch using normal policy-visible information. The three deal-in events followed a Riichi with five live waits and no legal Dama Ron Yaku, a Seven Pairs Riichi with three live waits, and an attacking one-Shanten Seven Pairs discard. These are not equivalent to execution failures. The review did not establish that a same-value, same-speed proven-safe alternative existed at those exact deal-in decisions. No claim is made that the losses were pure luck or that this change would reverse their outcomes.

The rejected one-Han opening and a Pon that did not improve an existing ready hand were consistent with South's current high-value preference. A two-Shanten discard that gave up six immediate improving copies had a slightly better bounded legal-completion forecast; immediate ukeire alone does not establish that it was an error. The forecasting model remains heuristic.

## Concrete gap

South's offensive ranking used the existing attack utility, Shanten, ukeire, Dora retention, pair retention and red-tile retention, then preferred drawn-tile disposal or tile-label ordering. It did not break a complete offensive tie with a tile already discarded by every current Riichi declarer. Seventeen potential equal-summary cases appeared across five recent sessions, including one in the losing-game review. This count does not independently verify every hidden ranking field for all seventeen cases.

Add an exact public-information tie-break after every existing offensive criterion and before the arbitrary drawn-tile/label tie-breaks. A candidate qualifies only if each declared/accepted Riichi opponent has discarded the same normalized tile kind. Red and regular fives share that public safety identity. No Riichi opponent means no new preference. This does not infer hidden waits, treat Suji as certain, trade away offense, or introduce folding. East speed ordering is unchanged.

For the recorded case, restore the original previous route and round-scoped policy memory before replay. With the new tie-break disabled, it chooses 5 Pin; enabled, it chooses 2 Pin. Both retain two Shanten, two projected Han and twenty improving copies. A memory-free replay gives different planning projections and must not be used to attribute those differences to this change. The relevant discard itself was not a recorded deal-in, so this is reduced unnecessary risk, not a demonstrated saved match.

The journal records discard_genbutsu_to_all_riichi for discard/Riichi proposals; terminal output remains recommended action only. Tests ensure the public safety preference cannot override a better projected Han, improving-copy count, Shanten, Dora retention or pair retention, and require safety against every Riichi declarer.

No live game, mouse input or agent launch was performed. Only aggregate findings and synthetic regression hands are published. Next: load the change for the user's next normal three-game batch and compare choices without claiming a win-rate improvement from a small sample.

Validation: full Mahjong suite passed 1,028 tests with one skipped. Existing recorded regressions now explicitly permit changed discard labels only when offensive route/value/progress and utility remain equal and the selected tile is proven genbutsu to every Riichi declarer.
