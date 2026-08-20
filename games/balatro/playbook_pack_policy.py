"""Compatibility alias for the Red/White playbook pack policy."""

import sys

from games.balatro.playbook.red_white import pack_policy as _impl

sys.modules[__name__] = _impl
