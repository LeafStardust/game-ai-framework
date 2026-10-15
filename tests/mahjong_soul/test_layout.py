from copy import deepcopy
import json
from pathlib import Path
import pytest
from games.mahjong_soul.live.runtime.layout import profile_for_size


def profile():
    return {"verified": True, "client_size": [925, 520], "slots": [[.5, .9]],
            "trigger": "ActionDealTile", "size_variants": [
                {"verified": True, "client_size": [1920, 1080], "slots": [[.51, .91]]}]}


def test_size_selection_uses_explicit_coordinates_and_keeps_source_independent():
    source = profile()
    assert profile_for_size(source, (925, 520))["slots"] == [[.5, .9]]
    result = profile_for_size(source, (1920, 1080))
    assert result["slots"] == [[.51, .91]]
    assert result["trigger"] == "ActionDealTile"
    result["slots"][0][0] = 0
    assert source["size_variants"][0]["slots"] == [[.51, .91]]


@pytest.mark.parametrize("bad", ["unknown", "unverified", "missing_points", "duplicate", "bad_size"])
def test_unverified_or_ambiguous_size_never_falls_back_to_scaling(bad):
    source = profile(); size = [1920, 1080]
    if bad == "unknown": size = [1600, 900]
    if bad == "unverified": source["size_variants"][0]["verified"] = False
    if bad == "missing_points": source["size_variants"][0].pop("slots")
    if bad == "duplicate": source["size_variants"].append(deepcopy(source["size_variants"][0]))
    if bad == "bad_size": size = [0, 1080]
    with pytest.raises(ValueError): profile_for_size(source, size)


def test_bundled_fullscreen_drawn_tile_maps_to_observed_center():
    path = Path(__file__).resolve().parents[2] / "games/mahjong_soul/live/layouts/discard-14-draw.json"
    result = profile_for_size(json.loads(path.read_text()), (1920, 1080))
    x, y = result["slots"][13]
    assert round(x * 1919) == 1532 and round(y * 1079) == 1000
    assert len(result["slots"]) == result["hand_count"] == 14


def test_client_geometry_tracks_window_origin_and_rejects_minimized_window():
    from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
    class User:
        minimized = False
        left, top = 50, 100
        def IsIconic(self, hwnd): return self.minimized
        def GetClientRect(self, hwnd, pointer):
            pointer._obj.right, pointer._obj.bottom = 925, 520
            return True
        def ClientToScreen(self, hwnd, pointer):
            pointer._obj.x, pointer._obj.y = self.left, self.top
            return True
    mouse = WindowsMouse.__new__(WindowsMouse); mouse.user = User()
    assert mouse._client_geometry(1) == {"width": 925, "height": 520, "left": 50, "top": 100}
    mouse.user.left = -1000
    assert mouse._client_geometry(1)["left"] == -1000
    mouse.user.minimized = True
    with pytest.raises(ValueError, match="minimized"): mouse._client_geometry(1)
