from __future__ import annotations

"""Red/White strategy-relationship weight calibration.

The relationship catalogue distinguishes defining Gold cores from ordinary Silver
support. The old 8/3/1/-8 geometry allowed three Silver supports (9) to outrank a
Gold core (8), left a Gold core below the configured commitment threshold (9), and
made one explicit Banned conflict merely cancel one Gold component. Red/White now
uses 10/3/1/-12 with commitment at 10 and maturity at 20.

The calibration is exposed through the Red/White playbook API and enforced again at
the tracker config boundary. The second guard keeps hypothetical/copied states and
callers with cached modifier mappings on the same effective contract. Future
cartridges remain free to use their own calibration.
"""

from games.balatro.playbook.red_white.core import BalatroPlaybook
from games.balatro.strategy import BalatroStrategyTracker


RED_WHITE_RELATIONSHIP_CALIBRATION = {
    "gold_evidence": 10.0,
    "silver_evidence": 3.0,
    "bronze_evidence": 1.0,
    "banned_evidence": -12.0,
    "commit_threshold": 10.0,
    "mature_threshold": 20.0,
}


def _identity(state) -> tuple[str, str]:
    deck = str(getattr(state, "deck_name", getattr(state, "deck", "")) or "").upper()
    stake = str(getattr(state, "stake_name", getattr(state, "stake", "")) or "").upper()
    return deck, stake


def install_strategy_relationship_calibration() -> None:
    if getattr(BalatroStrategyTracker, "_relationship_calibration_installed", False):
        return

    original_strategy_modifiers = BalatroPlaybook.strategy_modifiers

    def strategy_modifiers(self):
        configured = original_strategy_modifiers(self)
        if self.key == ("RED", "WHITE"):
            configured.update(RED_WHITE_RELATIONSHIP_CALIBRATION)
        return configured

    BalatroPlaybook.strategy_modifiers = strategy_modifiers

    original_config = BalatroStrategyTracker._config

    def _config(self, state):
        configured = original_config(self, state)
        if _identity(state) != ("RED", "WHITE"):
            return configured
        # Return an isolated mapping because playbook configuration is shared and
        # must not be mutated as a side effect of evaluation.
        effective = dict(configured)
        effective.update(RED_WHITE_RELATIONSHIP_CALIBRATION)
        return effective

    BalatroStrategyTracker._config = _config
    BalatroStrategyTracker._relationship_calibration_installed = True
