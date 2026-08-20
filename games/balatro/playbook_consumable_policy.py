"""Compatibility alias for the Red/White playbook consumable policy."""

import sys

from games.balatro.playbook.red_white import consumable_policy as _impl

sys.modules[__name__] = _impl
