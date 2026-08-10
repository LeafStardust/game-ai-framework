import argparse

from games.balatro.setup.installer import BalatroSetup, BalatroSetupError


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install and verify Balatro integration dependencies "
            "for game-ai-framework."
        )
    )
    parser.add_argument("--balatro-dir", default=None)
    parser.add_argument("--mods-dir", default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstall Lovely, Steamodded, and BalatroBot.",
    )
    args = parser.parse_args()

    try:
        setup = BalatroSetup(
            balatro_dir=args.balatro_dir,
            mods_dir=args.mods_dir,
            force=args.force,
        )
        report = setup.install()
    except BalatroSetupError as error:
        parser.error(str(error))

    print(f"Balatro: {report.paths.balatro_dir}")
    print(f"Mods:    {report.paths.mods_dir}")
    for name in report.installed:
        print(f"installed: {name}")
    for name in report.skipped:
        print(f"already installed: {name}")
    print("Balatro integration setup verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
