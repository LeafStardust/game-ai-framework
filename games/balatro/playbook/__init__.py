"""Balatro playbook package.

The active Red Deck / White Stake implementation lives in ``red_white``.
Future deck/stake playbooks live beside it while this package preserves the
historic ``games.balatro.playbook`` public import surface.
"""

from .red_white.core import *  # noqa: F401,F403
from .red_white.core import default_balatro_playbooks as _core_default_balatro_playbooks


# Five-run calibration on Red/White showed repeated D1 wall-clock exhaustion only
# after deck-growth effects pushed the deck into the low/mid 60s.  Keep the live
# horizon and wall-clock authority unchanged, but lower this cartridge's ordinary
# node ceiling so sampled deep search yields control back to the bounded fallback
# before the 8-second deadline.  Explicit CLI node overrides still bypass this
# value in the runtime runner.
RED_WHITE_LIVE_MAX_SEARCH_NODES = 2500


def default_balatro_playbooks():
    registry = _core_default_balatro_playbooks()
    playbook = registry.get("RED", "WHITE")
    planner = playbook.strategy.get("planner")
    if isinstance(planner, dict):
        planner["max_search_nodes"] = RED_WHITE_LIVE_MAX_SEARCH_NODES
    return registry
