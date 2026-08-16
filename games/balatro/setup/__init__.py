"""Compatibility aliases for Balatro installation discovery.

The former third-party integration installer (Lovely/Steamodded/BalatroBot) has
been removed. New code should import from games.balatro.installation directly.
"""

from games.balatro.installation import (
    BalatroInstallation as BalatroSetup,
    BalatroInstallationError as BalatroSetupError,
)

__all__ = ["BalatroSetup", "BalatroSetupError"]
