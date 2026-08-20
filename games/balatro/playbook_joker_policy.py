"""Compatibility alias for the Red/White playbook Joker policy."""

import sys

from games.balatro.playbook.red_white import joker_policy as _impl

sys.modules[__name__] = _impl
