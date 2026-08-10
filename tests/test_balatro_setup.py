import io
import zipfile

from games.balatro.setup import BalatroSetup


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_setup_installs_windows_dependencies(tmp_path, monkeypatch):
    balatro = tmp_path / "Balatro"
    balatro.mkdir()
    (balatro / "Balatro.exe").write_bytes(b"")
    mods = tmp_path / "Mods"

    lovely = _zip_bytes({"version.dll": b"lovely"})
    smods = _zip_bytes({"smods-release/manifest.json": b"{}"})
    balatrobot = _zip_bytes(
        {
            "balatrobot-release/balatrobot.json": b"{}",
            "balatrobot-release/balatrobot.lua": b"return true",
        }
    )

    metadata = {
        BalatroSetup.LOVELY_RELEASE: {
            "assets": [
                {
                    "name": "lovely-x86_64-pc-windows-msvc.zip",
                    "browser_download_url": "memory://lovely",
                }
            ]
        },
        BalatroSetup.SMODS_RELEASE: {
            "zipball_url": "memory://smods"
        },
        BalatroSetup.BALATROBOT_RELEASE: {
            "zipball_url": "memory://balatrobot"
        },
    }
    downloads = {
        "memory://lovely": lovely,
        "memory://smods": smods,
        "memory://balatrobot": balatrobot,
    }

    setup = BalatroSetup(
        balatro_dir=balatro,
        mods_dir=mods,
        system="Windows",
        json_getter=metadata.__getitem__,
        byte_getter=downloads.__getitem__,
    )
    report = setup.install()

    assert report.installed == ["Lovely", "Steamodded", "BalatroBot"]
    assert (balatro / "version.dll").read_bytes() == b"lovely"
    assert (mods / "smods" / "manifest.json").is_file()
    assert (mods / "balatrobot" / "balatrobot.json").is_file()


def test_setup_is_idempotent_when_dependencies_exist(tmp_path):
    balatro = tmp_path / "Balatro"
    balatro.mkdir()
    (balatro / "Balatro.exe").write_bytes(b"")
    (balatro / "version.dll").write_bytes(b"lovely")
    mods = tmp_path / "Mods"
    (mods / "smods").mkdir(parents=True)
    (mods / "smods" / "manifest.json").write_text("{}")
    (mods / "balatrobot").mkdir()
    (mods / "balatrobot" / "balatrobot.json").write_text("{}")

    def unexpected(_):
        raise AssertionError("network should not be used")

    setup = BalatroSetup(
        balatro_dir=balatro,
        mods_dir=mods,
        system="Windows",
        json_getter=unexpected,
        byte_getter=unexpected,
    )
    report = setup.install()

    assert report.installed == []
    assert report.skipped == ["Lovely", "Steamodded", "BalatroBot"]


def test_detects_balatro_in_secondary_steam_library(tmp_path, monkeypatch):
    steam = tmp_path / "Steam"
    secondary = tmp_path / "Games"
    config = steam / "steamapps"
    config.mkdir(parents=True)
    (config / "libraryfolders.vdf").write_text(
        f'"path" "{secondary}"',
        encoding="utf-8",
    )
    balatro = secondary / "steamapps/common/Balatro"
    balatro.mkdir(parents=True)
    (balatro / "Balatro.exe").write_bytes(b"")

    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path))
    monkeypatch.setattr(
        BalatroSetup,
        "_windows_steam_roots",
        classmethod(lambda cls: [steam]),
    )

    detected = BalatroSetup.detect_balatro_dir(system="Windows")

    assert detected == balatro.resolve()
