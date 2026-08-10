from __future__ import annotations

import argparse
import platform
from dataclasses import dataclass
from pathlib import Path

from .installer import BalatroSetup, BalatroSetupError


@dataclass(frozen=True)
class ExternalBalatroSetupReport:
    balatro_dir: Path
    injection_path: Path
    backup_path: Path
    changed: bool


class ExternalBalatroSetup:
    """Prepares Balatro for the unmodified external-control backend."""

    def __init__(
        self,
        balatro_dir: str | Path | None = None,
        *,
        system: str | None = None,
    ):
        self.system = system or platform.system()
        self.balatro_dir = BalatroSetup.detect_balatro_dir(
            balatro_dir,
            system=self.system,
        )

    @property
    def injection_path(self) -> Path:
        name = "liblovely.dylib" if self.system == "Darwin" else "version.dll"
        return self.balatro_dir / name

    @property
    def backup_path(self) -> Path:
        return self.injection_path.with_name(
            self.injection_path.name + ".game-ai-disabled"
        )

    def prepare(self) -> ExternalBalatroSetupReport:
        injection = self.injection_path
        backup = self.backup_path
        changed = False

        if injection.exists():
            if backup.exists():
                raise BalatroSetupError(
                    "cannot disable Lovely because the game-ai backup already exists: "
                    f"{backup}"
                )
            injection.rename(backup)
            changed = True

        self.validate()
        return ExternalBalatroSetupReport(
            balatro_dir=self.balatro_dir,
            injection_path=injection,
            backup_path=backup,
            changed=changed,
        )

    def restore_modding(self) -> ExternalBalatroSetupReport:
        injection = self.injection_path
        backup = self.backup_path
        changed = False

        if backup.exists():
            if injection.exists():
                raise BalatroSetupError(
                    "cannot restore Lovely because an injection library already exists: "
                    f"{injection}"
                )
            backup.rename(injection)
            changed = True

        return ExternalBalatroSetupReport(
            balatro_dir=self.balatro_dir,
            injection_path=injection,
            backup_path=backup,
            changed=changed,
        )

    def validate(self) -> None:
        if self.injection_path.exists():
            raise BalatroSetupError(
                "Lovely injection is still enabled: "
                f"{self.injection_path}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the normal Steam Balatro install for external AI control."
    )
    parser.add_argument("--balatro-dir", default=None)
    parser.add_argument(
        "--restore-modding",
        action="store_true",
        help="Restore a Lovely library previously disabled by this command.",
    )
    args = parser.parse_args()

    try:
        setup = ExternalBalatroSetup(balatro_dir=args.balatro_dir)
        report = (
            setup.restore_modding()
            if args.restore_modding
            else setup.prepare()
        )
    except BalatroSetupError as error:
        parser.error(str(error))

    print(f"Balatro: {report.balatro_dir}")
    if args.restore_modding:
        print("Lovely restored." if report.changed else "Lovely was not disabled.")
    else:
        print("Lovely disabled." if report.changed else "Lovely was already disabled.")
        print("External Steam mode verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
