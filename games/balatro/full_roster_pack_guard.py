from __future__ import annotations

"""Fail-closed Joker-pack capacity guard.

Opened Joker packs cannot safely select an ordinary Joker when the authoritative
modeled roster has no free slot.  Unlike SHOP replacement, PACK selection currently
has no explicit sell-then-select transaction in the autonomous action contract, so
non-Negative Joker choices must rank below Skip until capacity exists.  Negative
Jokers remain legal because they are slot-neutral in Balatro.
"""

from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


def _normalized_edition(choice) -> str:
    data = getattr(choice, "data", None)
    if not isinstance(data, dict):
        return ""
    edition = data.get("edition")
    if isinstance(edition, dict):
        edition = next((name for name, enabled in edition.items() if bool(enabled)), "")
    return str(edition or "").upper()


def _pack_joker_fits(state, choice) -> bool:
    if _normalized_edition(choice) == "NEGATIVE":
        return True
    jokers = tuple(getattr(state, "jokers", ()) or ())
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    return len(jokers) < slots


def install_full_roster_pack_guard() -> None:
    if getattr(BalatroPackPolicy, "_full_roster_pack_guard_installed", False):
        return

    original_score_joker = BalatroPackPolicy._score_joker

    def _score_joker(self, state, action, choice):
        if not _pack_joker_fits(state, choice):
            # Strictly below the default/positive Skip score.  This is a legality
            # guard, not a strategic value opinion: the bridge would reject the
            # corresponding PACK_SELECT with "joker slots are full".
            return PackActionScore(
                action,
                min(-1.0, float(getattr(self, "skip_bias", 0.35)) - 1.0),
                (
                    "pack Joker blocked: authoritative Joker capacity is full",
                    "non-Negative PACK_SELECT has no autonomous replacement transaction; prefer Skip",
                ),
            )
        return original_score_joker(self, state, action, choice)

    BalatroPackPolicy._score_joker = _score_joker
    BalatroPackPolicy._full_roster_pack_guard_installed = True
