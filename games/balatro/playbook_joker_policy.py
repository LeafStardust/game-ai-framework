"""Canonical public import for playbook-aware Joker acquisition.

Production historically imported a second threshold-only class from this module
while Bond conflict, pivot, retention, and Build Health policies wrapped the
Red/White implementation.  The two class objects silently diverged, so the live
runner bypassed those installed authorities.  Keep one public import path, but
make it an alias of the sole canonical implementation.
"""

from games.balatro.playbook.red_white.joker_policy import (  # noqa: F401
    PlaybookJokerAcquisitionPolicy,
)


__all__ = ("PlaybookJokerAcquisitionPolicy",)
