"""Balatro playbook package.

The active Red Deck / White Stake implementation lives in ``red_white``.
Future deck/stake playbooks live beside it while this package preserves the
historic ``games.balatro.playbook`` public import surface.
"""

from .red_white.core import *  # noqa: F401,F403
