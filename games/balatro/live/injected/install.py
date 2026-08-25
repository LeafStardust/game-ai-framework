from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import stat
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from games.balatro.setup.installer import (
    BalatroSetup,
    BalatroSetupError,
)


BRIDGE_ARCHIVE_NAME = "game_ai_framework_bridge.lua"
BACKUP_SUFFIX = ".gaf-original"
HOOK_BEGIN = "-- game-ai-framework bridge begin"
HOOK_END = "-- game-ai-framework bridge end"
_REPLACE_ATTEMPTS = 20
_REPLACE_DELAY = 0.1


class BalatroFusedPatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FusedPatchReport:
    executable: Path
    backup: Path
    runtime_dir: Path
    already_patched: bool
    reused_backup: bool


def asset_dir() -> Path:
    return Path(__file__).with_name("assets")


def bridge_asset_path() -> Path:
    return asset_dir() / "bridge.lua"


def default_runtime_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not available")
    return Path(appdata) / "Balatro" / "game-ai-framework-bridge"


def backup_path(executable: str | Path) -> Path:
    path = Path(executable)
    return path.with_name(path.name + BACKUP_SUFFIX)


def _load_hook() -> bytes:
    hook = (
        "\n"
        f"{HOOK_BEGIN}\n"
        f'local _gaf_bridge_chunk, _gaf_bridge_error = '
        f'love.filesystem.load("{BRIDGE_ARCHIVE_NAME}")\n'
        "assert(_gaf_bridge_chunk, _gaf_bridge_error)\n"
        "_gaf_bridge_chunk()\n"
        f"{HOOK_END}\n"
    )
    return hook.encode("utf-8")


def _patched_main(main_lua: bytes) -> tuple[bytes, bool]:
    marker = HOOK_BEGIN.encode("utf-8")
    if marker in main_lua:
        return main_lua, True
    return main_lua.rstrip(b"\r\n") + _load_hook(), False


def _bridge_with_runtime_hotfixes(bridge_lua: bytes) -> bytes:
    """Apply verified execution-only fixes to the production bridge payload.

    Custom bridge sources are supported by the fused patcher tests and by callers
    using ``bridge_source=``. They do not advertise a production bridge revision and
    must be embedded byte-for-byte rather than being rejected by a production-only
    migration.

    Production bridge revision 7 incorrectly rejects Negative Jokers when the
    ordinary Joker roster is full. For an identified revision-7 payload, normalize
    line endings in memory, require exactly one known capacity guard, patch that
    guard, and bump the embedded revision to 9. Revision 9 also identifies the
    source-level GAME_OVER pause-release restart repair. An identified production
    payload whose expected guard changed still fails closed.
    """
    if b"bridge_revision=7" not in bridge_lua:
        return bridge_lua

    normalized = bridge_lua.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if normalized.count(b"bridge_revision=7") != 1:
        raise BalatroFusedPatchError(
            "bridge revision marker changed; refusing to embed an unverified bridge"
        )

    old_guard = (
        b'    if set == "Joker" then\n'
        b'      local count = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_count or 0) or 0\n'
        b'      local limit = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_limit or 0) or 0\n'
        b'      if count >= limit then\n'
        b'        return false, "joker slots are full"\n'
        b'      end\n'
    )
    new_guard = (
        b'    if set == "Joker" then\n'
        b'      local count = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_count or 0) or 0\n'
        b'      local limit = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_limit or 0) or 0\n'
        b'      local negative = card and card.edition and card.edition.negative == true\n'
        b'      if count >= limit and not negative then\n'
        b'        return false, "joker slots are full"\n'
        b'      end\n'
    )
    if normalized.count(old_guard) != 1:
        raise BalatroFusedPatchError(
            "bridge Negative-slot hotfix target changed; refusing to embed an unverified bridge"
        )

    patched = normalized.replace(old_guard, new_guard, 1)
    return patched.replace(b"bridge_revision=7", b"bridge_revision=9", 1)


def _fused_archive(executable: Path) -> tuple[list[zipfile.ZipInfo], int, bytes]:
    if not executable.is_file():
        raise BalatroFusedPatchError(f"Balatro executable not found: {executable}")

    try:
        with executable.open("rb") as raw:
            if raw.read(2) != b"MZ":
                raise BalatroFusedPatchError(
                    f"{executable} is not a Windows PE executable"
                )

        with zipfile.ZipFile(executable, "r") as archive:
            infos = archive.infolist()
            if not infos:
                raise BalatroFusedPatchError(
                    "Balatro executable contains no fused LÖVE archive entries"
                )
            main_entries = [info for info in infos if info.filename == "main.lua"]
            if len(main_entries) != 1:
                raise BalatroFusedPatchError(
                    "expected exactly one main.lua in the fused LÖVE archive; "
                    f"found {len(main_entries)}"
                )
            prefix_size = min(info.header_offset for info in infos)
            if prefix_size <= 0:
                raise BalatroFusedPatchError(
                    "fused LÖVE executable prefix could not be identified"
                )
            main_lua = archive.read(main_entries[0])
    except BalatroFusedPatchError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise BalatroFusedPatchError(
            f"unable to read Balatro fused LÖVE archive: {error}"
        ) from error

    return infos, prefix_size, main_lua


def _copy_zipinfo(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    clone = zipfile.ZipInfo(info.filename, date_time=info.date_time)
    clone.compress_type = info.compress_type
    clone.comment = info.comment
    clone.extra = info.extra
    clone.internal_attr = info.internal_attr
    clone.external_attr = info.external_attr
    clone.create_system = info.create_system
    clone.create_version = info.create_version
    clone.extract_version = info.extract_version
    clone.flag_bits = info.flag_bits & ~0x08
    clone.volume = info.volume
    return clone


def _make_writable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if not (mode & stat.S_IWRITE):
        try:
            path.chmod(mode | stat.S_IWRITE)
        except OSError:
            pass


def _replace_with_retry(source: Path, destination: Path) -> None:
    _make_writable(destination)
    last_error: OSError | None = None
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(source, destination)
            return
        except PermissionError as error:
            last_error = error
            if attempt + 1 < _REPLACE_ATTEMPTS:
                time.sleep(_REPLACE_DELAY)
                continue
            break
        except OSError as error:
            last_error = error
            break

    detail = f": {last_error}" if last_error is not None else ""
    raise BalatroFusedPatchError(
        "unable to replace Balatro.exe after building and validating the patched "
        "archive. Close Balatro completely and make sure Steam is not currently "
        "verifying/updating the game. If the Steam library folder itself denies "
        "writes, run the terminal with permission to modify that library"
        + detail
    )


def _rewrite_fused_executable(
    executable: Path,
    *,
    bridge_source: Path,
) -> bool:
    infos, prefix_size, main_lua = _fused_archive(executable)
    patched_main, already_patched = _patched_main(main_lua)

    if not bridge_source.is_file():
        raise BalatroFusedPatchError(
            f"first-party bridge asset is missing: {bridge_source}"
        )
    bridge_lua = _bridge_with_runtime_hotfixes(bridge_source.read_bytes())

    with executable.open("rb") as source:
        prefix = source.read(prefix_size)
        if len(prefix) != prefix_size:
            raise BalatroFusedPatchError(
                "unable to read the complete Balatro executable prefix"
            )

    original_mode = executable.stat().st_mode
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=executable.name + ".",
        suffix=".tmp",
        dir=executable.parent,
    )
    os.close(temporary_fd)
    temporary = Path(temporary_name)

    try:
        temporary.write_bytes(prefix)
        with zipfile.ZipFile(executable, "r") as source_archive:
            with zipfile.ZipFile(
                temporary,
                "a",
                allowZip64=True,
            ) as destination:
                for info in infos:
                    if info.filename == BRIDGE_ARCHIVE_NAME:
                        continue
                    data = (
                        patched_main
                        if info.filename == "main.lua"
                        else source_archive.read(info)
                    )
                    destination.writestr(_copy_zipinfo(info), data)

                bridge_info = zipfile.ZipInfo(BRIDGE_ARCHIVE_NAME)
                bridge_info.compress_type = zipfile.ZIP_DEFLATED
                bridge_info.external_attr = 0o644 << 16
                destination.writestr(bridge_info, bridge_lua)

        _, _, verified_main = _fused_archive(temporary)
        if HOOK_BEGIN.encode("utf-8") not in verified_main:
            raise BalatroFusedPatchError(
                "patched executable validation did not find the bridge hook"
            )
        with zipfile.ZipFile(temporary, "r") as verified:
            if verified.read(BRIDGE_ARCHIVE_NAME) != bridge_lua:
                raise BalatroFusedPatchError(
                    "patched executable validation did not preserve the bridge"
                )

        temporary.chmod(original_mode | stat.S_IWRITE)
        _replace_with_retry(temporary, executable)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return already_patched


def patch_fused_game(
    executable: str | Path,
    *,
    bridge_source: str | Path | None = None,
    runtime_dir: str | Path | None = None,
) -> FusedPatchReport:
    executable_path = Path(executable).resolve()
    backup = backup_path(executable_path)
    bridge_path = (
        Path(bridge_source).resolve()
        if bridge_source is not None
        else bridge_asset_path()
    )

    _, _, main_lua = _fused_archive(executable_path)
    already_patched = HOOK_BEGIN.encode("utf-8") in main_lua
    reused_backup = False
    created_backup = False

    if not already_patched:
        if backup.exists():
            try:
                same = filecmp.cmp(executable_path, backup, shallow=False)
            except OSError as error:
                raise BalatroFusedPatchError(
                    f"unable to validate existing Balatro backup {backup}: {error}"
                ) from error
            if not same:
                raise BalatroFusedPatchError(
                    f"refusing to overwrite existing original backup: {backup}. "
                    "It differs from the current executable, so the installer "
                    "cannot safely infer whether it belongs to an interrupted "
                    "install. Restore/verify Balatro before retrying."
                )
            reused_backup = True
        else:
            try:
                shutil.copy2(executable_path, backup)
                created_backup = True
            except OSError as error:
                raise BalatroFusedPatchError(
                    f"unable to create Balatro backup at {backup}: {error}"
                ) from error

    try:
        _rewrite_fused_executable(
            executable_path,
            bridge_source=bridge_path,
        )
    except Exception:
        if created_backup and backup.is_file():
            try:
                backup.unlink()
            except OSError:
                pass
        raise

    runtime = (
        Path(runtime_dir)
        if runtime_dir is not None
        else default_runtime_dir()
    )
    try:
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / "command.txt").unlink(missing_ok=True)
        (runtime / "response.txt").unlink(missing_ok=True)
    except OSError as error:
        raise BalatroFusedPatchError(
            f"unable to prepare bridge runtime directory {runtime}: {error}"
        ) from error

    return FusedPatchReport(
        executable=executable_path,
        backup=backup,
        runtime_dir=runtime,
        already_patched=already_patched,
        reused_backup=reused_backup,
    )


def restore_fused_game(executable: str | Path) -> Path:
    executable_path = Path(executable).resolve()
    backup = backup_path(executable_path)
    if not backup.is_file():
        raise BalatroFusedPatchError(
            f"original Balatro backup not found: {backup}"
        )

    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=executable_path.name + ".restore.",
        suffix=".tmp",
        dir=executable_path.parent,
    )
    os.close(temporary_fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(backup, temporary)
        _replace_with_retry(temporary, executable_path)
        backup.unlink()
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return executable_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install the game-ai-framework first-party Balatro action bridge "
            "directly into Balatro's fused LÖVE archive. No Lovely, Steamodded, "
            "BalatroBot, or mouse calibration is required."
        )
    )
    parser.add_argument("--balatro-dir")
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Restore the exact original Balatro.exe backup.",
    )
    args = parser.parse_args()

    try:
        balatro_dir = BalatroSetup.detect_balatro_dir(args.balatro_dir)
        executable = balatro_dir / "Balatro.exe"
        if args.uninstall:
            restored = restore_fused_game(executable)
            print(f"Balatro -> {balatro_dir}")
            print(f"Restored original executable -> {restored}")
            print("Restart Balatro -> required")
            return 0

        report = patch_fused_game(executable)
    except (BalatroSetupError, BalatroFusedPatchError, OSError, RuntimeError) as error:
        parser.error(str(error))

    print(f"Balatro -> {balatro_dir}")
    print(f"Patched executable -> {report.executable}")
    print(f"Original backup -> {report.backup}")
    print(f"Existing backup reused -> {report.reused_backup}")
    print(f"Bridge runtime directory -> {report.runtime_dir}")
    print(
        "Existing bridge hook -> "
        f"{'updated' if report.already_patched else 'installed'}"
    )
    print("Injection method -> fused LÖVE archive patch")
    print("Runtime loader required -> False")
    print("Lovely required -> False")
    print("Steamodded required -> False")
    print("BalatroBot required -> False")
    print("Mouse calibration required -> False")
    print("Achievement-disable flag modified -> False")
    print("Restart Balatro -> required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
