from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from games.balatro.live.balatrobot_bridge import BalatroBotBridge
from games.balatro.setup import BalatroSetup, BalatroSetupError


class BalatroLaunchError(RuntimeError):
    pass


class BalatroLauncher:
    def __init__(
        self,
        endpoint: str = BalatroBotBridge.DEFAULT_ENDPOINT,
        balatro_dir: str | Path | None = None,
        *,
        fast: bool = False,
        headless: bool = False,
        popen: Callable[..., subprocess.Popen] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ):
        self.endpoint = endpoint
        self.balatro_dir = balatro_dir
        self.fast = fast
        self.headless = headless
        self.popen = popen or subprocess.Popen
        self.sleeper = sleeper or time.sleep

    def launch(self) -> subprocess.Popen:
        try:
            setup = BalatroSetup(balatro_dir=self.balatro_dir)
            setup.validate()
        except BalatroSetupError as error:
            raise BalatroLaunchError(
                f"Balatro integration is not set up: {error}. "
                "Run `py -m games.balatro.setup` first."
            ) from error

        if setup.system != "Windows":
            raise BalatroLaunchError(
                "automatic Balatro launch is currently supported on Windows; "
                "start Balatro manually on this platform"
            )

        executable = setup.paths.balatro_dir / "Balatro.exe"
        parsed = urlparse(self.endpoint)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 12346
        env = os.environ.copy()
        env.update(
            {
                "BALATROBOT_HOST": host,
                "BALATROBOT_PORT": str(port),
                "BALATROBOT_FAST": "1" if self.fast else "0",
                "BALATROBOT_HEADLESS": "1" if self.headless else "0",
            }
        )

        try:
            return self.popen(
                [str(executable)],
                cwd=str(setup.paths.balatro_dir),
                env=env,
            )
        except OSError as error:
            raise BalatroLaunchError(
                f"unable to launch Balatro: {error}"
            ) from error

    def wait_until_connected(
        self,
        bridge: BalatroBotBridge,
        *,
        timeout: float = 30.0,
        interval: float = 0.25,
    ) -> None:
        deadline = time.monotonic() + max(0.0, timeout)
        while time.monotonic() <= deadline:
            if bridge.is_connected():
                return
            self.sleeper(max(0.0, interval))
        raise BalatroLaunchError(
            f"BalatroBot API did not become available at {self.endpoint}"
        )
