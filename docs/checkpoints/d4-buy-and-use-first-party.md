# D4 Buy & Use first-party execution checkpoint

D4's shop-side `BUY_AND_USE_CONSUMABLE` execution foundation is complete on the production first-party injected path.

Cleared contract:

- Python bridge emits a dedicated `BUY_AND_USE_CONSUMABLE` command.
- The injected Lua bridge admits only visible Tarot, Planet, or Spectral shop items.
- The Lua bridge requires Balatro's native `buy_and_use_button` with `button=buy_from_shop` and `func=can_buy_and_use` before invoking `G.FUNCS.buy_from_shop`.
- The unified injected dispatcher verifies a fresh complete SHOP snapshot, exact offer-count reduction, disappearance of the selected live offer when a live id exists, and exact money deduction when public cost/money are available.
- No mouse fallback, hidden RNG, seed read, or future draw information is used.
- Focused D4/B6 injected regressions and the full local test suite were reported green before this checkpoint was recorded.

This closes only D4's production Buy & Use **execution** gap. It does not complete D4 decision intelligence. The active B6 + D4/D5/D6/D7 work still requires the dedicated three-way `IGNORE/HOLD -> BUY -> BUY_AND_USE` acquisition policy, plus broader held-consumable timing, targeting, and Planet strategy.

`ROADMAP.md` already marks "Buy & Use execution foundation" complete; this checkpoint records that the checked execution foundation is now specifically first-party injected and authoritatively reconciled rather than relying on legacy mouse validation.
