from __future__ import annotations

"""Opened-pack Skip uses the real sunk-cost baseline.

D8 decides whether buying an unopened booster is worth its money, interest, reserve,
and visible-shop opportunity cost.  Once that transaction has happened and the
agent is in a ``*_PACK`` phase, those acquisition costs are already sunk.  D9 must
therefore compare visible choices against doing nothing, not against the historical
positive ``skip_bias`` preference.

The policy changes only the production default.  Explicit ``skip_bias`` overrides
remain available to direct callers/tests that intentionally want a different
experimental baseline.
"""

from games.balatro.pack_policy import BalatroPackPolicy


OPENED_PACK_SKIP_BASELINE = 0.0


def install_pack_sunk_cost_policy() -> None:
    if getattr(BalatroPackPolicy, "_pack_sunk_cost_policy_installed", False):
        return

    original_init = BalatroPackPolicy.__init__

    def init(self, *args, **kwargs):
        if "skip_bias" not in kwargs:
            kwargs["skip_bias"] = OPENED_PACK_SKIP_BASELINE
        original_init(self, *args, **kwargs)

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._pack_sunk_cost_policy_installed = True
