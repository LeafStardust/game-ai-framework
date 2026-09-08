from __future__ import annotations

import os
import platform
import re
from pathlib import Path


class BalatroInstallationError(RuntimeError):
    pass


class BalatroInstallation:
    """Locate a local Steam Balatro installation without installing third-party mods."""

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
                raise BalatroInstallationError(
                    f"Balatro installation not found at {path}"
                )
            return path

        for path in cls._balatro_candidates(current_system):
            if cls._looks_like_balatro(path, current_system):
                return path.resolve()

        raise BalatroInstallationError(
            "unable to detect Balatro. Pass --balatro-dir explicitly."
        )

    @classmethod
    def _balatro_candidates(cls, system: str) -> list[Path]:
        if system == "Windows":
            roots = cls._windows_steam_roots()
        elif system == "Darwin":
            roots = [Path.home() / "Library/Application Support/Steam"]
        elif system == "Linux":
            roots = [
                Path.home() / ".local/share/Steam",
                Path.home() / ".steam/steam",
            ]
        else:
            return []

        candidates: list[Path] = []
        for root in roots:
            candidates.append(root / "steamapps/common/Balatro")
            candidates.extend(cls._library_candidates(root))
        return cls._dedupe_paths(candidates)

    @classmethod
    def _windows_steam_roots(cls) -> list[Path]:
        roots: list[Path] = []
        for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
            value = os.environ.get(variable)
            if value:
                roots.append(Path(value) / "Steam")

        try:
            import winreg

            keys = (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                (
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\WOW6432Node\Valve\Steam",
                ),
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
    def _dedupe_paths(paths: list[Path]) -> list[Path]:
        result: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path)
            if key not in seen:
                seen.add(key)
                result.append(path)
        return result
