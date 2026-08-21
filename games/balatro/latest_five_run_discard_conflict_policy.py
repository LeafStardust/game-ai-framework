from __future__ import annotations

"""Five-run calibration for mutually exclusive discard/no-discard engines.

Burnt Joker needs the first discard each round. Green Joker loses Mult whenever a
discard is used, and Burglar removes all discards at round start. These mechanics
must not be treated as one coherent engine. Burglar remains positive support for
Green/no-discard play; the conflict is specifically against Burnt's discard engine.
"""

from dataclasses import replace

from games.balatro.strategy import BalatroStrategyTracker, build_component_strategy_index


_BURNT = frozenset({"burnt", "burntjoker"})
_GREEN = frozenset({"green", "greenjoker"})
_BURGLAR = frozenset({"burglar", "burglarjoker"})


def _ban(definition, tokens: frozenset[str]):
    """Move exact Joker tokens out of positive tiers and into Banned."""
    return replace(
        definition,
        gold_jokers=frozenset(set(definition.gold_jokers) - set(tokens)),
        silver_jokers=frozenset(set(definition.silver_jokers) - set(tokens)),
        bronze_jokers=frozenset(set(definition.bronze_jokers) - set(tokens)),
        banned_jokers=frozenset(set(definition.banned_jokers) | set(tokens)),
    )


def install_latest_five_run_discard_conflict_policy() -> None:
    if getattr(BalatroStrategyTracker, "_latest_five_run_discard_conflict_installed", False):
        return

    original_init = BalatroStrategyTracker.__init__

    def __init__(self, definitions, *args, **kwargs):
        calibrated = dict(definitions)

        # Burnt requires a real discard. Green punishes that discard and Burglar
        # removes the action entirely, so neither can support the Burnt engine.
        if "burnt_joker_engine" in calibrated:
            calibrated["burnt_joker_engine"] = _ban(
                calibrated["burnt_joker_engine"],
                _GREEN | _BURGLAR,
            )

        # Conversely, Burnt is a mechanical conflict for the two explicit
        # no-discard leaves. Existing Green<->Burglar positive relationships remain
        # untouched and are resolved by the state-aware Section Eleven rules.
        for strategy_id in ("no_discard_green", "no_discard_burglar"):
            if strategy_id in calibrated:
                calibrated[strategy_id] = _ban(calibrated[strategy_id], _BURNT)

        original_init(self, calibrated, *args, **kwargs)
        self.component_index = build_component_strategy_index(self.definitions)

    BalatroStrategyTracker.__init__ = __init__
    BalatroStrategyTracker._latest_five_run_discard_conflict_installed = True
