from games.balatro.live.injected.install import (
    _bridge_with_runtime_hotfixes,
    bridge_asset_path,
)


def test_installed_bridge_allows_negative_joker_at_full_roster():
    patched = _bridge_with_runtime_hotfixes(bridge_asset_path().read_bytes())

    assert b"bridge_revision=8" in patched
    assert b"card.edition and card.edition.negative == true" in patched
    assert b"if count >= limit and not negative then" in patched


def test_installed_bridge_still_blocks_ordinary_joker_at_full_roster():
    patched = _bridge_with_runtime_hotfixes(bridge_asset_path().read_bytes())

    assert b'return false, "joker slots are full"' in patched
