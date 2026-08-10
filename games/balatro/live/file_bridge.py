import json
import os
from pathlib import Path

from games.balatro.live.interfaces import BalatroLiveBridge
from games.balatro.live.protocol import (
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


class FileBalatroBridge(BalatroLiveBridge):
    """JSON file transport for the live Balatro bridge mod."""

    def __init__(self, directory: Path | None = None):
        self.directory = directory or self.default_directory()
        self.state_path = self.directory / "state.json"
        self.command_path = self.directory / "command.json"

    @staticmethod
    def default_directory() -> Path:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is required for the default Balatro bridge path")
        return Path(appdata) / "Balatro" / "game_ai_bridge"

    def observe(self) -> LiveBalatroSnapshot:
        data = json.loads(
            self.state_path.read_text(encoding="utf-8")
        )

        return LiveBalatroSnapshot(
            sequence=int(data["sequence"]),
            phase=str(data["phase"]),
            state_complete=bool(data["state_complete"]),
            payload=dict(data.get("payload", {})),
        )

    def send(self, command: LiveBalatroCommand) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary_path = self.command_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(
                {
                    "sequence": command.sequence,
                    "action": command.action,
                    "payload": command.payload,
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        temporary_path.replace(self.command_path)

    def is_connected(self) -> bool:
        return self.state_path.is_file()
