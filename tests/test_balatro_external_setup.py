import pytest

from games.balatro.setup.external import ExternalBalatroSetup
from games.balatro.setup.installer import BalatroSetupError


def _balatro(tmp_path):
    balatro = tmp_path / "Balatro"
    balatro.mkdir()
    (balatro / "Balatro.exe").write_bytes(b"")
    return balatro


def test_external_setup_disables_lovely_reversibly(tmp_path):
    balatro = _balatro(tmp_path)
    lovely = balatro / "version.dll"
    lovely.write_bytes(b"lovely")

    setup = ExternalBalatroSetup(balatro, system="Windows")
    report = setup.prepare()

    assert report.changed is True
    assert not lovely.exists()
    assert report.backup_path.read_bytes() == b"lovely"

    restored = setup.restore_modding()

    assert restored.changed is True
    assert lovely.read_bytes() == b"lovely"
    assert not report.backup_path.exists()


def test_external_setup_is_idempotent_when_lovely_is_absent(tmp_path):
    balatro = _balatro(tmp_path)
    setup = ExternalBalatroSetup(balatro, system="Windows")

    report = setup.prepare()

    assert report.changed is False
    setup.validate()


def test_external_setup_rejects_conflicting_backup(tmp_path):
    balatro = _balatro(tmp_path)
    (balatro / "version.dll").write_bytes(b"new")
    (balatro / "version.dll.game-ai-disabled").write_bytes(b"old")
    setup = ExternalBalatroSetup(balatro, system="Windows")

    with pytest.raises(BalatroSetupError):
        setup.prepare()
