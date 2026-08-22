"""Compatibility entrypoint for the canonical Balatro live monitor.

Bond/composition telemetry now lives directly in ``balatro_agent_monitor``. This
module remains only so older local launch commands fail over cleanly without
reconstructing any retired strategy tiers or target lists.
"""

from .balatro_agent_monitor import *  # noqa: F401,F403
from .balatro_agent_monitor import main


if __name__ == "__main__":
    raise SystemExit(main())
