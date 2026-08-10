from games.balatro.live.launcher import BalatroLauncher


def test_launcher_starts_windows_balatro_with_api_environment(
    tmp_path,
    monkeypatch,
):
    balatro = tmp_path / "Balatro"
    balatro.mkdir()
    (balatro / "Balatro.exe").write_bytes(b"")
    (balatro / "version.dll").write_bytes(b"lovely")

    appdata = tmp_path / "AppData/Roaming"
    mods = appdata / "Balatro/Mods"
    (mods / "smods").mkdir(parents=True)
    (mods / "smods" / "manifest.json").write_text("{}")
    (mods / "balatrobot").mkdir()
    (mods / "balatrobot" / "balatrobot.json").write_text("{}")
    monkeypatch.setenv("APPDATA", str(appdata))

    calls = []

    class Process:
        pass

    def popen(command, **kwargs):
        calls.append((command, kwargs))
        return Process()

    monkeypatch.setattr("platform.system", lambda: "Windows")
    launcher = BalatroLauncher(
        endpoint="http://127.0.0.1:23456",
        balatro_dir=balatro,
        fast=True,
        headless=True,
        popen=popen,
    )

    process = launcher.launch()

    assert isinstance(process, Process)
    command, kwargs = calls[0]
    assert command == [str(balatro / "Balatro.exe")]
    assert kwargs["cwd"] == str(balatro)
    assert kwargs["env"]["BALATROBOT_HOST"] == "127.0.0.1"
    assert kwargs["env"]["BALATROBOT_PORT"] == "23456"
    assert kwargs["env"]["BALATROBOT_FAST"] == "1"
    assert kwargs["env"]["BALATROBOT_HEADLESS"] == "1"


def test_launcher_waits_until_bridge_is_connected():
    class Bridge:
        def __init__(self):
            self.calls = 0

        def is_connected(self):
            self.calls += 1
            return self.calls >= 3

    bridge = Bridge()
    launcher = BalatroLauncher(sleeper=lambda _: None)

    launcher.wait_until_connected(
        bridge,
        timeout=1,
        interval=0,
    )

    assert bridge.calls == 3
