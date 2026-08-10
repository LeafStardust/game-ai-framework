from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import shutil
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import Request, urlopen


class BalatroSetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BalatroSetupPaths:
    balatro_dir: Path
    mods_dir: Path

    @property
    def lovely_path(self) -> Path:
        if platform.system() == "Darwin":
            return self.balatro_dir / "liblovely.dylib"
        return self.balatro_dir / "version.dll"


@dataclass
class BalatroSetupReport:
    paths: BalatroSetupPaths
    installed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


class BalatroSetup:
    LOVELY_RELEASE = (
        "https://api.github.com/repos/ethangreen-dev/"
        "lovely-injector/releases/latest"
    )
    SMODS_RELEASE = (
        "https://api.github.com/repos/Steamodded/smods/releases/latest"
    )
    BALATROBOT_RELEASE = (
        "https://api.github.com/repos/coder/balatrobot/releases/latest"
    )

    def __init__(
        self,
        balatro_dir: str | Path | None = None,
        mods_dir: str | Path | None = None,
        *,
        system: str | None = None,
        force: bool = False,
        json_getter: Callable[[str], dict] | None = None,
        byte_getter: Callable[[str], bytes] | None = None,
    ):
        self.system = system or platform.system()
        detected_balatro = self.detect_balatro_dir(
            balatro_dir,
            system=self.system,
        )
        detected_mods = (
            Path(mods_dir).expanduser().resolve()
            if mods_dir is not None
            else self.detect_mods_dir(
                detected_balatro,
                system=self.system,
            )
        )
        self.paths = BalatroSetupPaths(
            balatro_dir=detected_balatro,
            mods_dir=detected_mods,
        )
        self.force = force
        self.json_getter = json_getter or self._get_json
        self.byte_getter = byte_getter or self._get_bytes

    def install(self) -> BalatroSetupReport:
        self._validate_balatro_directory()
        self.paths.mods_dir.mkdir(parents=True, exist_ok=True)
        report = BalatroSetupReport(self.paths)

        self._install_lovely(report)
        self._install_repo_release(
            report,
            "Steamodded",
            self.SMODS_RELEASE,
            self.paths.mods_dir / "smods",
            "manifest.json",
        )
        self._install_repo_release(
            report,
            "BalatroBot",
            self.BALATROBOT_RELEASE,
            self.paths.mods_dir / "balatrobot",
            "balatrobot.json",
        )
        self.validate()
        return report

    def validate(self) -> None:
        missing = []
        lovely = self._lovely_target()
        if not lovely.is_file():
            missing.append(str(lovely))
        if not (self.paths.mods_dir / "smods" / "manifest.json").is_file():
            missing.append("Steamodded manifest")
        if not (
            self.paths.mods_dir / "balatrobot" / "balatrobot.json"
        ).is_file():
            missing.append("BalatroBot manifest")

        if missing:
            raise BalatroSetupError(
                "Balatro integration setup is incomplete: "
                + ", ".join(missing)
            )

    def _install_lovely(self, report: BalatroSetupReport) -> None:
        target = self._lovely_target()
        if target.exists() and not self.force:
            report.skipped.append("Lovely")
            return

        release = self.json_getter(self.LOVELY_RELEASE)
        asset = self._lovely_asset(release)
        archive = self.byte_getter(asset["browser_download_url"])
        self._verify_digest(archive, asset.get("digest"))

        if asset["name"].endswith(".zip"):
            data = self._read_zip_member(archive, target.name)
        else:
            data = self._read_tar_member(archive, target.name)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        report.installed.append("Lovely")

    def _install_repo_release(
        self,
        report: BalatroSetupReport,
        name: str,
        release_url: str,
        destination: Path,
        marker: str,
    ) -> None:
        if (destination / marker).is_file() and not self.force:
            report.skipped.append(name)
            return

        release = self.json_getter(release_url)
        archive_url = release.get("zipball_url")
        if not archive_url:
            raise BalatroSetupError(f"{name} release has no source archive")

        archive = self.byte_getter(archive_url)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            self._extract_zip(archive, temp)
            roots = [path for path in temp.iterdir() if path.is_dir()]
            if len(roots) != 1:
                raise BalatroSetupError(
                    f"unexpected {name} release archive layout"
                )

            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(roots[0], destination)

        if not (destination / marker).is_file():
            raise BalatroSetupError(
                f"{name} archive did not contain {marker}"
            )
        report.installed.append(name)

    def _lovely_asset(self, release: dict) -> dict:
        assets = release.get("assets") or []
        machine = platform.machine().lower()

        if self.system == "Darwin":
            expected = (
                "lovely-aarch64-apple-darwin.tar.gz"
                if machine in {"arm64", "aarch64"}
                else "lovely-x86_64-apple-darwin.tar.gz"
            )
        elif self.system in {"Windows", "Linux"}:
            expected = "lovely-x86_64-pc-windows-msvc.zip"
        else:
            raise BalatroSetupError(
                f"unsupported platform for automatic Lovely setup: {self.system}"
            )

        for asset in assets:
            if asset.get("name") == expected:
                return asset
        raise BalatroSetupError(
            f"Lovely release does not contain expected asset: {expected}"
        )

    def _lovely_target(self) -> Path:
        if self.system == "Darwin":
            return self.paths.balatro_dir / "liblovely.dylib"
        return self.paths.balatro_dir / "version.dll"

    def _validate_balatro_directory(self) -> None:
        if not self._looks_like_balatro(self.paths.balatro_dir, self.system):
            raise BalatroSetupError(
                f"Balatro installation not found at {self.paths.balatro_dir}"
            )

    @classmethod
    def detect_balatro_dir(
        cls,
        explicit: str | Path | None = None,
        *,
        system: str | None = None,
    ) -> Path:
        current_system = system or platform.system()
        if explicit is not None:
            path = Path(explicit).expanduser().resolve()
            if not cls._looks_like_balatro(path, current_system):
                raise BalatroSetupError(
                    f"Balatro installation not found at {path}"
                )
            return path

        for path in cls._balatro_candidates(current_system):
            if cls._looks_like_balatro(path, current_system):
                return path.resolve()

        raise BalatroSetupError(
            "unable to detect Balatro. Pass --balatro-dir explicitly."
        )

    @classmethod
    def detect_mods_dir(
        cls,
        balatro_dir: Path,
        *,
        system: str | None = None,
    ) -> Path:
        current_system = system or platform.system()
        home = Path.home()

        if current_system == "Windows":
            appdata = os.environ.get("APPDATA")
            if not appdata:
                raise BalatroSetupError("APPDATA is not available")
            return Path(appdata) / "Balatro" / "Mods"

        if current_system == "Darwin":
            return home / "Library/Application Support/Balatro/Mods"

        if current_system == "Linux":
            steam_root = cls._steam_root_from_balatro(balatro_dir)
            return (
                steam_root
                / "steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/"
                "AppData/Roaming/Balatro/Mods"
            )

        raise BalatroSetupError(
            f"unsupported platform for automatic Mods path: {current_system}"
        )

    @classmethod
    def _balatro_candidates(cls, system: str) -> list[Path]:
        if system == "Windows":
            roots = cls._windows_steam_roots()
        elif system == "Darwin":
            roots = [
                Path.home() / "Library/Application Support/Steam"
            ]
        elif system == "Linux":
            roots = [
                Path.home() / ".local/share/Steam",
                Path.home() / ".steam/steam",
            ]
        else:
            return []

        candidates = []
        for root in roots:
            candidates.append(root / "steamapps/common/Balatro")
            candidates.extend(cls._library_candidates(root))
        return cls._dedupe_paths(candidates)

    @classmethod
    def _windows_steam_roots(cls) -> list[Path]:
        roots = []
        for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
            value = os.environ.get(variable)
            if value:
                roots.append(Path(value) / "Steam")

        try:
            import winreg

            keys = (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Valve\Steam"),
            )
            for hive, key_name in keys:
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        value, _ = winreg.QueryValueEx(key, "InstallPath")
                        roots.append(Path(value))
                except OSError:
                    continue
        except ImportError:
            pass

        return cls._dedupe_paths(roots)

    @classmethod
    def _library_candidates(cls, steam_root: Path) -> list[Path]:
        config = steam_root / "steamapps/libraryfolders.vdf"
        if not config.is_file():
            return []

        try:
            text = config.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        paths = re.findall(r'"path"\s+"([^"]+)"', text)
        return [
            Path(value.replace("\\\\", "\\"))
            / "steamapps/common/Balatro"
            for value in paths
        ]

    @staticmethod
    def _looks_like_balatro(path: Path, system: str) -> bool:
        if system == "Darwin":
            return (path / "Balatro.app").exists()
        return (path / "Balatro.exe").is_file()

    @staticmethod
    def _steam_root_from_balatro(path: Path) -> Path:
        resolved = path.resolve()
        if len(resolved.parents) < 3:
            raise BalatroSetupError(
                "unable to determine Steam root from Balatro path"
            )
        return resolved.parents[2]

    @staticmethod
    def _dedupe_paths(paths: list[Path]) -> list[Path]:
        result = []
        seen = set()
        for path in paths:
            key = str(path)
            if key not in seen:
                seen.add(key)
                result.append(path)
        return result

    @staticmethod
    def _verify_digest(data: bytes, digest: str | None) -> None:
        if not digest or not digest.startswith("sha256:"):
            return
        expected = digest.split(":", 1)[1].lower()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise BalatroSetupError("downloaded Lovely archive failed SHA256 verification")

    @staticmethod
    def _read_zip_member(data: bytes, filename: str) -> bytes:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            matches = [
                name for name in archive.namelist()
                if Path(name).name == filename
            ]
            if len(matches) != 1:
                raise BalatroSetupError(
                    f"archive did not contain exactly one {filename}"
                )
            return archive.read(matches[0])

    @staticmethod
    def _read_tar_member(data: bytes, filename: str) -> bytes:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            matches = [
                member for member in archive.getmembers()
                if Path(member.name).name == filename and member.isfile()
            ]
            if len(matches) != 1:
                raise BalatroSetupError(
                    f"archive did not contain exactly one {filename}"
                )
            file = archive.extractfile(matches[0])
            if file is None:
                raise BalatroSetupError(f"unable to extract {filename}")
            return file.read()

    @staticmethod
    def _extract_zip(data: bytes, destination: Path) -> None:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            base = destination.resolve()
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if target != base and base not in target.parents:
                    raise BalatroSetupError("unsafe path in release archive")
            archive.extractall(destination)

    @staticmethod
    def _get_json(url: str) -> dict:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "game-ai-framework",
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _get_bytes(url: str) -> bytes:
        request = Request(
            url,
            headers={"User-Agent": "game-ai-framework"},
        )
        with urlopen(request, timeout=60) as response:
            return response.read()
