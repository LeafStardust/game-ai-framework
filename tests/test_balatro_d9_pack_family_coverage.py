from pathlib import Path

from games.balatro.live.external.d9_pack_family_coverage import (
    REQUIRED_FAMILIES,
    append_record,
    classify_pack_family,
    coverage_summary,
    load_records,
)
from games.balatro.live.pack import LivePackChoice


def _choice(kind: str, label: str = "X") -> LivePackChoice:
    data = {
        "area_index": 0,
        "address": 0x1000,
        "live_id": 500,
        "label": label,
        "ability_name": label,
        "ability_set": kind,
    }
    return LivePackChoice(area_index=0, address=0x1000, data=data)


def test_d9_family_classifier_maps_all_five_pack_choice_kinds():
    assert classify_pack_family([_choice("Joker")]) == "JOKER"
    assert classify_pack_family([_choice("PLAYING_CARD")]) == "STANDARD"
    assert classify_pack_family([_choice("Planet")]) == "PLANET"
    assert classify_pack_family([_choice("Tarot")]) == "TAROT"
    assert classify_pack_family([_choice("Spectral")]) == "SPECTRAL"


def test_d9_family_classifier_rejects_mixed_or_unrecognized_choices():
    try:
        classify_pack_family([_choice("Joker"), _choice("Tarot")])
    except ValueError as error:
        assert "homogeneous pack family" in str(error)
    else:
        raise AssertionError("mixed D9 pack family should fail closed")

    try:
        classify_pack_family([_choice("Unknown")])
    except ValueError as error:
        assert "homogeneous pack family" in str(error)
    else:
        raise AssertionError("unknown D9 pack family should fail closed")


def test_d9_family_coverage_accumulates_without_claiming_missing_families(tmp_path: Path):
    path = tmp_path / "coverage.jsonl"
    append_record(path, {"family": "JOKER", "recommendation": {"action": "SELECT_PACK_CARD"}})
    append_record(path, {"family": "SPECTRAL", "recommendation": {"action": "SKIP_BOOSTER"}})

    records = load_records(path)
    summary = coverage_summary(records)

    assert len(records) == 2
    assert summary["observed"] == ("JOKER", "SPECTRAL")
    assert summary["missing"] == ("STANDARD", "PLANET", "TAROT")
    assert not summary["complete"]


def test_d9_family_coverage_only_completes_after_every_required_family_is_recorded():
    records = [{"family": family} for family in REQUIRED_FAMILIES]

    summary = coverage_summary(records)

    assert summary["observed"] == REQUIRED_FAMILIES
    assert summary["missing"] == ()
    assert summary["complete"]
