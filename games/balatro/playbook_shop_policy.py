"""Compatibility alias for the Red/White playbook shop policy."""

import sys

from games.balatro.playbook.red_white import shop_policy as _impl

sys.modules[__name__] = _impl
