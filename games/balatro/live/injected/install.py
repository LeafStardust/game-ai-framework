from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from games.balatro.setup.installer import (
    BalatroSetup,
    BalatroSetupError,
)


BRIDGE_MOD_NAME = "game-ai-framework-bridge"
ASSET_NAMES = ("lovely.toml", "bridge.lua")


def asset_dir() -> Path:
    return Path(__file__).with_name("assets")


def default_mods_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not available")
    return Path(appdata) / "Balatro" / "Mods"


def default_runtime_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not available")
    return Path(appdata) / "Balatro" / "game-ai-framework-bridge"


def install_bridge_assets(
    destination: str | Path,
    *,
    source: str | Path | None = None,
) -> Path:
    destination_path = Path(destination)
    source_path = Path(source) if source is not None else asset_dir()
    destination_path.mkdir(parents=True, exist_ok=True)

    for name in ASSET_NAMES:
        source_file = source_path / name
        if not source_file.is_file():
            raise FileNotFoundError(
                f"missing injected bridge asset: {source_file}"
            )
        shutil.copy2(source_file, destination_path / name)

    return destination_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install the game-ai-framework first-party Balatro action bridge. "
            "Lovely is the only loader dependency; Steamodded and BalatroBot "
            "are not required."
        )
    )
    parser.add_argument("--balatro-dir")
    parser.add_argument("--mods-dir")
    args = parser.parse_args()

    try:
        balatro_dir = BalatroSetup.detect_balatro_dir(args.balatro_dir)
    except BalatroSetupError as error:
        parser.error(str(error))

    lovely_path = balatro_dir / "version.dll"
    if not lovely_path.is_file():
        parser.error(
            "Lovely is not installed in the Balatro directory. "
            "The first-party bridge needs a Lua injector/loader, but it does "
            "not need Steamodded or BalatroBot."
        )

    try:
        mods_dir = (
            Path(args.mods_dir)
            if args.mods_dir
            else default_mods_dir()
        )
        destination = install_bridge_assets(
            mods_dir / BRIDGE_MOD_NAME
        )
        runtime_dir = default_runtime_dir()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "command.txt").unlink(missing_ok=True)
        (runtime_dir / "response.txt").unlink(missing_ok=True)
    except (OSError, RuntimeError, FileNotFoundError) as error:
        parser.error(str(error))

    print(f"Balatro -> {balatro_dir}")
    print(f"Lovely loader -> {lovely_path}")
    print(f"First-party bridge mod -> {destination}")
    print(f"Bridge runtime directory -> {runtime_dir}")
    print("Steamodded required -> False")
    print("BalatroBot required -> False")
    print("Mouse calibration required -> False")
    print("Restart Balatro -> required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
